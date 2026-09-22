_INSERT = (
    "insert into raw_captures "
    "(source_type, source_url, content_text, image_path, source_handle, via_handle, "
    "submitted_store, content_hash, captured_at) "
    "values (%(source_type)s, %(source_url)s, %(content_text)s, %(image_path)s, "
    "%(source_handle)s, %(via_handle)s, %(submitted_store)s, %(content_hash)s, "
    "coalesce(%(captured_at)s::timestamptz, now())) "
    "on conflict (content_hash) do nothing "
    "returning id"
)


def insert_captures(conn, captures):
    """Insert RawCaptures, deduping on content_hash. Returns a list of
    {capture, id, inserted} where inserted is False for a duplicate."""
    results = []
    with conn.cursor() as cur:
        for cap in captures:
            cur.execute(
                _INSERT,
                {
                    "source_type": cap.source_type,
                    "source_url": cap.source_url,
                    "content_text": cap.content_text,
                    "image_path": cap.image_path,
                    "source_handle": cap.source_handle,
                    "via_handle": cap.via_handle,
                    "submitted_store": cap.submitted_store,
                    "content_hash": cap.content_hash,
                    "captured_at": cap.captured_at,
                },
            )
            row = cur.fetchone()
            results.append({"capture": cap, "id": row[0] if row else None, "inserted": row is not None})
    conn.commit()
    return results
