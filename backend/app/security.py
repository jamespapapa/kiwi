from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException


def normalize_existing_dir(path: str) -> Path:
    target = Path(path).expanduser()
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail="존재하는 폴더 경로가 아닙니다.")
    return target.resolve()


def is_inside(root: str | Path, candidate: str | Path) -> bool:
    try:
        root_abs = os.path.normcase(os.path.abspath(str(Path(root).resolve())))
        candidate_abs = os.path.normcase(os.path.abspath(str(Path(candidate).resolve())))
        return os.path.commonpath([root_abs, candidate_abs]) == root_abs
    except (OSError, ValueError):
        return False


def assert_inside(root: str | Path, candidate: str | Path) -> Path:
    target = Path(candidate).expanduser().resolve()
    if not is_inside(root, target):
        raise HTTPException(status_code=403, detail="프로젝트 루트 밖 경로 접근은 차단되었습니다.")
    return target


def safe_join(root: str | Path, *parts: str) -> Path:
    return assert_inside(root, Path(root).joinpath(*parts))
