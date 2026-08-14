"""Lane 3 — bulk graph content: file upload → staging → materialize.

For graph-shaped domain data at volume. Three operations chained:

1. ``create-file-upload`` — presign an S3 URL + register the file
2. upload the bytes to the presigned URL
3. ``ingest-file`` — stage into the platform's staging tables (small
   files stage synchronously; large files return a pending envelope
   with an ``operation_id`` you can monitor)
4. ``materialize`` — staging → graph

Combined with the per-graph schema operations (``add-node-table`` /
``add-relationship-table``) this stands up a complete custom knowledge
graph through the public surface.
"""

from __future__ import annotations

from pathlib import Path

from robosystems_client.api.content_operations import (
  create_file_upload as _create_file_upload,
)
from robosystems_client.api.content_operations import (
  ingest_file as _ingest_file,
)
from robosystems_client.api.graph_operations import (
  materialize as _materialize,
)
from robosystems_client.models import FileUploadRequest, IngestFileOp, MaterializeOp

from integration.client import IntegrationClient

_CONTENT_TYPES = {
  ".parquet": "application/x-parquet",
  ".csv": "text/csv",
  ".json": "application/json",
}


def upload_file(
  client: IntegrationClient,
  path: Path,
  *,
  table_name: str,
  ingest_to_graph: bool = False,
) -> dict:
  """Upload one file and stage it into ``table_name``.

  Set ``ingest_to_graph=True`` to auto-materialize after staging;
  otherwise call :func:`materialize` once all files are staged.
  """
  content_type = _CONTENT_TYPES.get(path.suffix, "application/octet-stream")
  upload_envelope = client.unwrap(
    _create_file_upload.sync_detailed(
      client.config.graph_id,
      client=client.sdk,
      body=FileUploadRequest.from_dict(
        {
          "file_name": path.name,
          "content_type": content_type,
          "table_name": table_name,
        }
      ),
    )
  )
  upload = upload_envelope["result"]
  client.upload_presigned(upload["upload_url"], path.read_bytes(), content_type)
  return client.unwrap(
    _ingest_file.sync_detailed(
      client.config.graph_id,
      client=client.sdk,
      body=IngestFileOp.from_dict(
        {"file_id": upload["file_id"], "ingest_to_graph": ingest_to_graph}
      ),
    )
  )


def materialize(client: IntegrationClient) -> dict:
  """Materialize everything staged into the graph."""
  return client.unwrap(
    _materialize.sync_detailed(
      client.config.graph_id,
      client=client.sdk,
      body=MaterializeOp.from_dict({}),
    )
  )
