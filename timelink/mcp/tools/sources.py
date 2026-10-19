"""Source-update pipeline tools (§3.11–3.17).

The library's single blocking ``db.update_from_sources`` call is split
into three tools the agent orchestrates: ``translate_sources`` (request
translations, returns immediately), ``wait_for_translations`` (bounded
wait with the library's retry semantics) and ``import_from_sources``
(import what is ready). ``get_import_status`` is the polling view;
``get_import_report`` / ``get_translation_report`` inspect errors.

All tools in this group ensure a Kleio server is attached (started in
Docker or attached per the TIMELINK_MCP_* configuration); query-only
tools elsewhere never touch Docker.
"""

from __future__ import annotations

import logging
import time

from timelink.kleio import KleioFile
from timelink.kleio.importer import import_from_xml
from timelink.mcp.context import get_context
from timelink.mcp.errors import tool_errors as _wrapped
from timelink.mcp.paging import json_safe

logger = logging.getLogger(__name__)

TERMINAL_TRANSLATION_STATUSES = {"V", "W", "E"}


def _kleio_file_record(kfile: KleioFile) -> dict:
    """A compact, JSON-safe view of a KleioFile for status listings."""
    return {
        "path": kfile.path,
        "name": kfile.name,
        "directory": kfile.directory,
        "status": kfile.status.value if kfile.status else None,
        "errors": kfile.errors,
        "warnings": kfile.warnings,
        "import_status": kfile.import_status.value if kfile.import_status else None,
        "import_errors": kfile.import_errors,
        "import_warnings": kfile.import_warnings,
        "xml_url": kfile.xml_url,
        "rpt_url": kfile.rpt_url,
        "modified_string": kfile.modified_string,
        "translated_string": kfile.translated_string,
        "imported_string": kfile.imported_string,
    }


def _db_and_server(database: str):
    ctx = get_context()
    db = ctx.databases.get(database)
    return ctx, db, ctx.kleio.ensure_attached(db)


def _source_path(ctx, database: str, path: str | None) -> str:
    """Resolve a tool's ``path`` argument to a Kleio-server path.

    None/"" (the default) scopes to the database's own project —
    ``projects/<project>/sources`` in a multi-project home, ``sources``
    in a single-project home — so one project's update never touches
    another's files. An explicit path overrides; "/" reaches the whole
    server.
    """
    if path:
        return path
    project = ctx.databases.project_of(database)
    if project:
        return f"projects/{project}/sources"
    return "sources"


def _import_status(db, path: str, recurse: bool, status: str | None):
    """db.get_import_status with a duplicate-name fallback.

    The library matches imported records by file name by default and
    raises when the listing contains repeated names (common in project
    trees, e.g. ``b1685.cli`` under several source sets); retry by full
    path, which the database records always carry.
    """
    try:
        return db.get_import_status(path=path, recurse=recurse, status=status)
    except ValueError:
        return db.get_import_status(path=path, recurse=recurse, status=status, match_path=True)


def translate_sources(
    database: str,
    path: str | None = None,
    recurse: bool = True,
    force: bool = False,
) -> dict:
    """Request translations on the Kleio server for the stale sources,
    without waiting. First step of the update pipeline; follow with
    ``wait_for_translations`` (or poll ``get_import_status``) and then
    ``import_from_sources``.

    Args:
        database: database name as shown by ``list_databases``.
        path: Kleio-server-relative path; None (default) scopes to the
            database's project sources; an explicit path overrides.
        recurse: recurse into subdirectories.
        force: request translation of every file, not only stale ones.

    Returns:
        ``{requested: [{path, status}], count, source_path}`` — the
        status each file had when its translation was requested.
    """
    ctx, db, kserver = _db_and_server(database)
    source_path = _source_path(ctx, database, path)
    status_filter = None if force else "T"  # None lists all files
    files = kserver.get_translations(path=source_path, recurse=recurse, status=status_filter)
    requested = []
    for kfile in files:
        kserver.translate(kfile.path, recurse="no", spawn="no")
        requested.append({"path": kfile.path, "status": kfile.status.value})
    ctx.kleio.remember_translate_request(ctx.databases.db_key(database), source_path, recurse, [f.path for f in files])
    return {
        "database": database,
        "source_path": source_path,
        "requested": requested,
        "count": len(requested),
    }


def wait_for_translations(
    database: str,
    files: list[str] | None = None,
    max_wait: int = 120,
) -> dict:
    """Block until the translations requested by the last
    ``translate_sources`` call (or the explicit ``files`` list) reach a
    terminal status, then report. Bounded by ``max_wait`` — re-invoke
    while ``still_pending`` is non-empty.

    A file that reverts from queued/processing back to needs-translation
    failed; it is re-requested once, and reported in ``failed`` if it
    fails again (same semantics as the library's internal wait).

    Args:
        database: database name as shown by ``list_databases``.
        files: explicit Kleio server paths to wait for; default: the
            paths from the last ``translate_sources`` call.
        max_wait: maximum seconds to wait before returning with
            ``still_pending``.

    Returns:
        ``{finished: [{path, status}], failed: [{path, reason}],
        still_pending: [path], waited_seconds}``.
    """
    ctx, db, kserver = _db_and_server(database)
    request = ctx.kleio.last_translate_request(ctx.databases.db_key(database))
    paths = list(files) if files else (request.paths if request else [])
    if not paths:
        return {
            "database": database,
            "finished": [],
            "failed": [],
            "still_pending": [],
            "waited_seconds": 0,
            "note": "no translations pending; call translate_sources first " "or pass an explicit files list",
        }
    source_path = request.source_path if request else _source_path(ctx, database, None)
    recurse = request.recurse if request else True

    pending = set(paths)
    active: set[str] = set()  # files ever seen queued/processing
    retried: set[str] = set()
    finished: dict[str, str] = {}
    failed: dict[str, str] = {}
    start = time.time()
    deadline = start + max_wait
    while pending and time.time() < deadline:
        listing = kserver.get_translations(path=source_path, recurse=recurse)
        statuses = {f.path: f.status.value for f in listing}
        for rpath in list(pending):
            status = statuses.get(rpath)
            if status in ("P", "Q"):
                active.add(rpath)
            elif status in TERMINAL_TRANSLATION_STATUSES:
                pending.discard(rpath)
                finished[rpath] = status
            elif status == "T" and rpath in active:
                if rpath not in retried:
                    retried.add(rpath)
                    active.discard(rpath)
                    logger.warning("Translation of %s failed; retrying", rpath)
                    kserver.translate(rpath, recurse="no", spawn="no")
                else:
                    pending.discard(rpath)
                    failed[rpath] = "translation failed twice"
        if pending:
            time.sleep(1)

    still_pending = sorted(pending)
    result = {
        "database": database,
        "finished": [{"path": p, "status": s} for p, s in sorted(finished.items())],
        "failed": [{"path": p, "reason": r} for p, r in sorted(failed.items())],
        "still_pending": still_pending,
        "waited_seconds": round(time.time() - start, 1),
    }
    if still_pending:
        result["note"] = "not all translations finished; re-invoke to keep waiting"
    return result


def import_from_sources(
    database: str,
    path: str | None = None,
    recurse: bool = True,
    force: bool = False,
    with_import_errors: bool = False,
    with_import_warnings: bool = False,
    with_translation_errors: bool = False,
    with_translation_warnings: bool = True,
    match_path: bool = False,
) -> dict:
    """Import into the database the files whose translations are ready and
    that are new or updated since the last import. Final step of the
    update pipeline (after ``translate_sources`` / ``wait_for_translations``).

    Args:
        database: database name as shown by ``list_databases``.
        path: Kleio-server-relative path; None (default) scopes to the
            database's project sources; an explicit path overrides.
        recurse: recurse into subdirectories.
        force: import every translated file, ignoring import status.
        with_import_errors: retry files that previously failed to import.
        with_import_warnings: retry files imported with warnings.
        with_translation_errors: also import translations that finished
            with errors.
        with_translation_warnings: also import translations that finished
            with warnings (default True).
        match_path: match database records by full path instead of filename.

    Returns:
        ``{imported: [{path, stats}], skipped: [{path, reason}]}`` with the
        per-file import stats the library only logs.
    """
    ctx, db, kserver = _db_and_server(database)
    source_path = _source_path(ctx, database, path)
    to_import: dict[str, KleioFile] = {}
    statuses = ["V"]
    if with_translation_warnings:
        statuses.append("W")
    if with_translation_errors:
        statuses.append("E")
    for status in statuses:
        for kfile in kserver.get_translations(path=source_path, recurse=recurse, status=status):
            to_import[kfile.path] = kfile

    if force:
        import_needed = list(to_import.values())
    else:
        try:
            import_needed = db.get_need_import(
                list(to_import.values()),
                with_import_errors=with_import_errors,
                with_import_warnings=with_import_warnings,
                match_path=match_path,
            )
        except ValueError:
            # duplicate file names in scope: match by full path instead
            if match_path:
                raise
            import_needed = db.get_need_import(
                list(to_import.values()),
                with_import_errors=with_import_errors,
                with_import_warnings=with_import_warnings,
                match_path=True,
            )

    imported, skipped = [], []
    for kfile in import_needed:
        with db.session() as session:
            try:
                stats = import_from_xml(
                    kfile.xml_url,
                    session=session,
                    options={
                        "return_stats": True,
                        "kleio_token": kserver.get_token(),
                        "kleio_url": kserver.get_url(),
                        "mode": "TL",
                    },
                )
                imported.append({"path": kfile.path, "stats": json_safe(stats)})
            except Exception as exc:
                session.rollback()
                logger.error("Import of %s failed: %s", kfile.path, exc)
                skipped.append({"path": kfile.path, "reason": str(exc)})
                continue
        time.sleep(1)  # pace the kleio server, as db.update_from_sources does

    return {
        "database": database,
        "imported": imported,
        "skipped": skipped,
        "counts": {
            "candidates": len(to_import),
            "imported": len(imported),
            "skipped": len(skipped),
        },
    }


def get_import_status(
    database: str,
    path: str | None = None,
    recurse: bool = True,
    status: str | None = None,
) -> dict:
    """Import/translation status of the Kleio files relative to this
    database — the "what would the update pipeline do / what happened"
    view, before and after updates.

    Args:
        database: database name as shown by ``list_databases``.
        path: Kleio-server-relative path; None (default) scopes to the
            database's project sources; an explicit path overrides.
        recurse: recurse into subdirectories.
        status: filter by import status: ``N`` new, ``U`` translation
            updated (reimport needed), ``I`` imported, ``W`` imported
            with warnings, ``E`` imported with errors.

    Returns:
        ``{files: [...], count}`` — per file: translation status
        (``V/W/E/T/P/Q``), errors, warnings, import status
        (``N/U/I/W/E``) and the report urls.
    """
    ctx, db, _ = _db_and_server(database)
    files = _import_status(db, _source_path(ctx, database, path), recurse, status)
    records = [_kleio_file_record(f) for f in files]
    return {"database": database, "files": records, "count": len(records)}


def get_import_report(database: str, file: str, match_path: bool = False) -> dict:
    """The import error/warning report stored in the database for one file.

    Args:
        database: database name as shown by ``list_databases``.
        file: file name or full path, as shown by ``get_import_status``.
        match_path: match by full path instead of filename only.
    """
    _, db, _ = _db_and_server(database)
    return {
        "database": database,
        "file": file,
        "report": db.get_import_rpt(file, match_path=match_path),
    }


def get_translation_report(database: str, file: str) -> dict:
    """The Kleio-server translation report for one file.

    Args:
        database: database name as shown by ``list_databases``.
        file: Kleio server path or file name, as shown by
            ``get_import_status``.
    """
    ctx, db, kserver = _db_and_server(database)
    # search the project scope first, the whole server as fallback
    listing = kserver.get_translations(path=_source_path(ctx, database, None), recurse=True)
    kfile = next((f for f in listing if f.path == file or f.name == file), None)
    if kfile is None:
        listing = kserver.get_translations(path="", recurse=True)
        kfile = next((f for f in listing if f.path == file or f.name == file), None)
    if kfile is None:
        raise ValueError(f"file '{file}' not found on the Kleio server; list files with get_import_status")
    if not kfile.rpt_url:
        return {
            "database": database,
            "file": kfile.path,
            "report": None,
            "note": "no translation report yet (file not translated)",
        }
    return {"database": database, "file": kfile.path, "report": kserver.get_report(kfile)}


def kleio_server_info() -> dict:
    """URL, version, home directory and health of the Kleio server used
    by the update tools (never the token). For diagnosing failed updates.
    """
    ctx = get_context()
    try:
        server = ctx.kleio.get_server()
    except Exception as exc:
        return {"attached": False, "error": str(exc)}
    version_info = server.get_version_info()
    return {
        "attached": True,
        "url": server.get_url(),
        "kleio_home": server.get_kleio_home(),
        "version_info": list(version_info) if version_info else None,
    }


def register(mcp) -> None:
    """Attach this module's tools to the FastMCP server."""
    mcp.tool(
        name="translate_sources",
        description=(
            "Update pipeline step 1: request translations on the Kleio server for "
            "the stale sources (or all with force=true), returning immediately. "
            "With no path argument, only the database's own project sources are "
            "touched. Follow with wait_for_translations, then import_from_sources. "
            "Poll get_import_status for the overall picture."
        ),
    )(_wrapped(translate_sources))
    mcp.tool(
        name="wait_for_translations",
        description=(
            "Update pipeline step 2: wait (bounded by max_wait seconds) for the "
            "translations requested by the last translate_sources call — or an "
            "explicit files list — to finish. Re-invoke while still_pending is "
            "non-empty. Failed translations are retried once, matching the "
            "library's behaviour."
        ),
    )(_wrapped(wait_for_translations))
    mcp.tool(
        name="import_from_sources",
        description=(
            "Update pipeline step 3: import into the database the files whose "
            "translations are ready and that are new/updated since the last "
            "import. With no path argument, only the database's own project "
            "sources are considered. Returns per-file import stats and skipped "
            "files with reasons; inspect errors with get_import_report / "
            "get_translation_report."
        ),
    )(_wrapped(import_from_sources))
    mcp.tool(
        name="get_import_status",
        description=(
            "Import and translation status of the Kleio files relative to this "
            "database: translation status V/W/E/T/P/Q, import status N/U/I/W/E, "
            "error/warning counts, report urls. Defaults to the database's own "
            "project sources; use before and after the update pipeline, and to "
            "pick files for the report tools."
        ),
    )(_wrapped(get_import_status))
    mcp.tool(
        name="get_import_report",
        description=(
            "The import error/warning report stored in the database for one file "
            "(by name or full path as shown by get_import_status)."
        ),
    )(_wrapped(get_import_report))
    mcp.tool(
        name="get_translation_report",
        description=(
            "The Kleio-server translation report for one file (by path or name " "as shown by get_import_status)."
        ),
    )(_wrapped(get_translation_report))
    mcp.tool(
        name="kleio_server_info",
        description=(
            "URL, Kleio version, home directory and health of the Kleio server "
            "used by the update tools (the token is never included). For "
            "diagnosing failed updates."
        ),
    )(_wrapped(kleio_server_info))
