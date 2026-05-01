# Data model: incidents, transcripts, audio

How the three artefacts of a voice-driven incident report tie together.

## The three records

Each voice-driven incident produces three kinds of record across two
storage backends:

1. **Incident report** in Firebase Realtime Database
2. **Transcript** (text + metadata) in Firebase Realtime Database
3. **Audio blob** in Firebase Storage (or local disk in dev mode)

A single incident can have **many transcripts**, each with its own
optional audio blob. The schema is built for this from day one - the
multi-recording UX just exposes it.

## Primary keys

All three use Firebase RTDB push IDs (20-char URL-safe base64 starting
with `-`). They're generated server-side on insert:

| Record | RTDB path | Primary key |
|---|---|---|
| Incident | `incidentForms/{incidentId}` | `incidentId` |
| Transcript | `transcripts/{transcriptId}` | `transcriptId` |
| Client (sub-record of incident) | `clients/{clientId}` | `clientId` |

Push IDs are time-ordered, globally unique within the project, and safe
to use directly in URLs (no special characters).

## Foreign keys and the back-references

The relationship is **bidirectional**. The owning incident lists its
children, and each child also points back at the incident. This is
intentional - it lets you walk the graph from either direction without
extra joins.

### Incident → transcripts

`incidentForms/{incidentId}/transcriptIds` is an array of transcriptIds.
Maintained by `push_transcript()` in `app/services/firebase_client.py`,
which uses an RTDB transaction so concurrent appends don't lose entries.

### Transcript → incident

`transcripts/{transcriptId}/incidentId` stores the parent incidentId.
Set on creation, never modified. The audio upload route uses this back-
reference to enforce that a transcript can't be reattached to a
different incident.

### Incident → clients

Same pattern: `incidentForms/{incidentId}/clientList` is an array of
clientIds. Each `clients/{clientId}/incidentId` points back.

## Audio blob path

The third artefact is the audio blob. It's identified by a path that
encodes both foreign keys, making it self-describing:

```
audio/{incidentId}/{transcriptId}.{ext}
```

Where `{ext}` is `webm`, `m4a`, `ogg`, `mp3`, or `bin` depending on what
the browser produced.

Examples:

```
audio/-OqzbN9ZKpXR12345abcd/-OqzbZk8JmFh67890wxyz.webm
audio/-OqzbN9ZKpXR12345abcd/-OqzcD4HjLp34567abcde.webm   <- second recording, same incident
```

That folder structure is what makes multi-recording natural - all of an
incident's audio lives in one folder, named after the incident.

The path is stored on the transcript at `transcripts/{transcriptId}/audioPath`.
It is NOT a public URL - the backend mints a fresh signed URL on every
read. Production never persists a long-lived URL.

## Storage backend

Two backends, selected by env var:

| Backend | Selected when | File location |
|---|---|---|
| Firebase Storage | `FIREBASE_STORAGE_BUCKET` set | `gs://{bucket}/audio/{incidentId}/{transcriptId}.{ext}` |
| Local disk (dev) | `AUDIO_LOCAL_DIR` set | `{AUDIO_LOCAL_DIR}/audio/{incidentId}/{transcriptId}.{ext}` |

Both write the same relative path so the rest of the pipeline (signed
URLs, delete cascade, audit) is identical. Production sets
`FIREBASE_STORAGE_BUCKET`. Local dev typically sets `AUDIO_LOCAL_DIR`
so test recordings stay on the developer's machine.

Both modes are private. Firebase Storage uses v4 signed URLs (1-hour
TTL by default, override via `AUDIO_SIGNED_URL_TTL_SECONDS`). Local
mode serves via FastAPI's StaticFiles mount at `/local-audio/...` -
same-origin so playback works without auth headers, and only ever
enabled in dev.

## Cascade delete

`DELETE /api/forms/incident/{form_id}` deletes everything in this
order, with logging for any partial failure:

1. **Storage blobs first**, while RTDB still has the `transcriptIds`
   pointers in case something fails and we need to retry.
2. **Transcript records** under `transcripts/{tid}`.
3. **Client records** under `clients/{cid}`.
4. **Incident itself** at `incidentForms/{incidentId}`.

If a storage delete fails the function still proceeds to RTDB cleanup
and returns a summary dict. Tested by `test_audio_upload_roundtrip` in
`tests/e2e/test_transcripts.py`.

## Multi-recording: what's natural in this model

Because each transcript already has its own primary key and its own
audio blob, the data model handles N recordings per incident with no
schema change. The UI just needs to:

- Let the volunteer record, stop, then record again
- Save each segment as a separate transcript record on submit
- Display the resulting list of transcripts in the modal (already does)

In the storage layout, multiple recordings for one incident look like:

```
audio/<incidentId>/
  ├── <transcriptId-1>.webm   (first segment, e.g. 8:42 PM)
  ├── <transcriptId-2>.webm   (second segment, 8:51 PM)
  └── <transcriptId-3>.webm   (third segment, 9:03 PM)
```

The timestamp the user sees in the UI comes from
`transcripts/{tid}/createdDate`, which is set server-side on insert.
The file name on disk uses the transcript's push ID rather than a
timestamp - push IDs are already time-ordered (so files sort
chronologically) and unique (no collision risk if two recordings happen
to start in the same millisecond).

If you want a timestamp-named file on disk you can rename in the dev-
only local mode by changing `upload_audio` in
`app/services/firebase_client.py`, but production should keep the
push-ID names because GCS object names are immutable and renames mean
copy-then-delete.
