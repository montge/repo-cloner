"""Concurrent repository cloning with parallel processing."""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import git


@dataclass
class CloneResult:
    """Result of a clone operation."""

    url: str
    path: str
    success: bool
    duration: float
    error: Optional[str] = None


class ConcurrentCloner:
    """Clone multiple repositories concurrently using thread pool."""

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize concurrent cloner.

        Args:
            max_workers: Maximum number of concurrent workers.
                        Defaults to CPU count if not specified.
        """
        if max_workers is None:
            max_workers = os.cpu_count() or 4
        self.max_workers = max_workers

    def clone_multiple(
        self,
        repos: List[Dict[str, str]],
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> List[CloneResult]:
        """
        Clone multiple repositories concurrently.

        Args:
            repos: List of repository dicts with 'url' and 'path' keys
            progress_callback: Optional callback function(repo_url, status)

        Returns:
            List of CloneResult objects
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all clone tasks
            future_to_repo = {
                executor.submit(self._clone_single, repo, progress_callback): repo for repo in repos
            }

            # Collect results as they complete
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    # Should not happen since _clone_single catches exceptions
                    results.append(
                        CloneResult(
                            url=repo["url"],
                            path=repo["path"],
                            success=False,
                            duration=0.0,
                            error=str(exc),
                        )
                    )

        return results

    def _clone_single(
        self, repo: Dict[str, str], progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> CloneResult:
        """
        Clone a single repository.

        Args:
            repo: Repository dict with 'url' and 'path' keys
            progress_callback: Optional callback function(repo_url, status)

        Returns:
            CloneResult object
        """
        url = repo["url"]
        path = repo["path"]

        if progress_callback:
            progress_callback(url, "started")

        start_time = time.time()

        try:
            git.Repo.clone_from(url, path)
            duration = time.time() - start_time

            if progress_callback:
                progress_callback(url, "completed")

            return CloneResult(url=url, path=path, success=True, duration=duration)

        except Exception as exc:
            duration = time.time() - start_time

            if progress_callback:
                progress_callback(url, "failed")

            return CloneResult(url=url, path=path, success=False, duration=duration, error=str(exc))

    def clone_with_retry(self, repo: Dict[str, str], max_retries: int = 3) -> CloneResult:
        """
        Clone a repository with retry logic.

        Args:
            repo: Repository dict with 'url' and 'path' keys
            max_retries: Maximum number of retry attempts

        Returns:
            CloneResult object
        """
        url = repo["url"]
        path = repo["path"]

        last_error = None

        for attempt in range(max_retries):
            start_time = time.time()

            try:
                git.Repo.clone_from(url, path)
                duration = time.time() - start_time

                return CloneResult(url=url, path=path, success=True, duration=duration)

            except Exception as exc:
                last_error = str(exc)
                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)

        # All retries failed
        return CloneResult(url=url, path=path, success=False, duration=0.0, error=last_error)

    def get_summary(self, results: List[CloneResult]) -> Dict[str, Any]:
        """
        Generate summary statistics from clone results.

        Args:
            results: List of CloneResult objects

        Returns:
            Dictionary with summary statistics:
            - total: int
            - successful: int
            - failed: int
            - success_rate: float
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful

        success_rate = (successful / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(success_rate, 2),
        }
