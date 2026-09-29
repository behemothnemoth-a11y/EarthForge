# Redfield Acquisition Network Client

The Redfield POC base-acquisition script uses Windows `curl.exe` rather than
`Invoke-WebRequest`.

Reason:

- the target development shell is Windows PowerShell 5.1;
- `Invoke-WebRequest` showed endpoint/TLS behavior that prevented otherwise
  valid Overpass requests;
- `curl.exe` provides stable URL-encoded POST behavior and clear exit codes.

The Overpass query is written to the ignored local downloads directory and sent
with `--data-urlencode data@<query-file>`.

The downloaded response is accepted only when:

1. curl exits successfully;
2. the response exists and is non-trivial in size;
3. PowerShell can parse it as JSON;
4. it contains an Overpass `elements` array.

Only after those checks does EarthForge run the normalizer.
