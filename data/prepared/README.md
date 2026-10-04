# Basel shade snapshot v1

This versioned snapshot restores the existing building and compact survey loaders
without provider requests. From the repository root, with the project environment:

```sh
python scripts/install_shade_snapshot.py
python scripts/prepare_building_shade.py --offline
```

Installation verifies the archive, every extracted file, and the pinned route,
inventory and configuration hashes before publishing files to ignored local
`.cache/buildings/` and `data/geometry/`. Repeating the command is safe. Differing
local data is preserved unless you explicitly use `--replace`. Stop the server
before replacing an existing dataset, then restart it. Archive files and manifests
are committed in ordinary Git; no Git LFS or separate provider download is needed.

The building dataset contains 17,432 sanitized footprints/parts acquired on
2026-10-04. Its source date is unknown. Support is constrained to Basel-Stadt and
the saved route halo; unsupported coverage stays unknown. The survey manifest
retains all locally prepared, checksum-verified assets and their original
preparation versions, missing-data flags and coverage gaps. This package does not
claim complete city coverage or physical shade accuracy. It excludes acquisition
checkpoints, raw provider tags, native source downloads and other app caches.
Browser libraries, basemap images and observation/fountain snapshots still use
their separate preparation commands.

## Data licences and attribution

The building database is © OpenStreetMap contributors and distributed under
[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
The editable, sanitized JSON database is included in the archive. Preserve this
notice and the ODbL when redistributing or adapting that database. Original
mapped heights remain separate from the survey grids; the archive is a collection
of separately attributed datasets.

The compact survey grids are derived from swissSURFACE3D Raster and swissALTI3D:
**© swisstopo**. Their [open-data terms](https://www.swisstopo.admin.ch/en/faq-free-geodata)
permit publication and reuse with source attribution. Source URLs, source hashes,
survey years, transformation settings and output hashes remain in the geometry
manifest. These data licences are distinct from the repository's software licence.

See the [source register](../../docs/SOURCES.md) for model limitations and provider
details. To update this snapshot, create a new named archive and metadata file
from verified prepared inputs, retain attribution, review the expanded contents
with the privacy guard, and update the installer's snapshot reference.
