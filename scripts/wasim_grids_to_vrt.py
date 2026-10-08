#!/usr/bin/env python3
"""
Generate GDAL VRT sidecar files for WaSiM-ETH binary grid files.

WaSiM binary grids have a 48-byte header of 12 little-endian float32 values:
  [0] ncols   [1] nrows   [2] xllcorner  [3] yllcorner
  [4] cellsize [5] nodata  [6..11] WaSiM-internal fields

The remaining bytes are ncols*nrows float32 values in row-major order.

Usage:
    # single file
    python wasim_grids_to_vrt.py grids/r500.use

    # all binary grids in a directory
    python wasim_grids_to_vrt.py grids/r500.*

    # override CRS (default: EPSG:21781, Swiss LV03)
    python wasim_grids_to_vrt.py --crs EPSG:2056 grids/r500.use
"""

import struct
import sys
from pathlib import Path

HEADER_BYTES = 48  # 12 * 4 bytes
HEADER_FLOATS = 12
FLOAT_SIZE = 4
DEFAULT_CRS = "EPSG:21781"  # Swiss LV03; change to EPSG:2056 for LV95


def read_header(path: Path) -> dict:
    """Read and decode the 12-float WaSiM binary header."""
    raw = path.read_bytes()[:HEADER_BYTES]
    if len(raw) < HEADER_BYTES:
        raise ValueError(f"File too small to contain a WaSiM header ({len(raw)} bytes)")
    fields = struct.unpack("<12f", raw)
    return {
        "ncols": int(round(fields[0])),
        "nrows": int(round(fields[1])),
        "xllcorner": fields[2],
        "yllcorner": fields[3],
        "cellsize": fields[4],
        "nodata": fields[5],
    }


def is_wasim_grid(path: Path, hdr: dict) -> bool:
    """Sanity-check: file size must equal header + ncols*nrows*4."""
    expected = HEADER_BYTES + hdr["ncols"] * hdr["nrows"] * FLOAT_SIZE
    return path.stat().st_size == expected


def make_vrt(datafile: Path, hdr: dict, crs: str) -> str:
    ncols = hdr["ncols"]
    nrows = hdr["nrows"]
    xll = hdr["xllcorner"]
    yll = hdr["yllcorner"]
    cs = hdr["cellsize"]
    nd = hdr["nodata"]

    yul = yll + nrows * cs  # top edge = yllcorner + nrows * cellsize
    line_offset = ncols * FLOAT_SIZE  # row-major: bytes between row starts

    return f"""\
<VRTDataset rasterXSize="{ncols}" rasterYSize="{nrows}">
  <SRS dataAxisToSRSAxisMapping="1,2">{crs}</SRS>
  <!-- GeoTransform: xmin, xres, xskew, ymax, yskew, -yres -->
  <GeoTransform>{xll}, {cs}, 0, {yul}, 0, -{cs}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1" subClass="VRTRawRasterBand">
    <Description>{datafile.name}</Description>
    <NoDataValue>{nd}</NoDataValue>
    <SourceFilename relativeToVRT="1">{datafile.name}</SourceFilename>
    <ImageOffset>{HEADER_BYTES}</ImageOffset>  <!-- skip the 48-byte WaSiM header -->
    <PixelOffset>{FLOAT_SIZE}</PixelOffset>    <!-- row-major: adjacent pixels are 4 bytes apart -->
    <LineOffset>{line_offset}</LineOffset>     <!-- row-major: {ncols} cols * 4 bytes = {line_offset} -->
    <ByteOrder>LSB</ByteOrder>                 <!-- little-endian -->
  </VRTRasterBand>
</VRTDataset>
"""


def process(path: Path, crs: str) -> None:
    try:
        hdr = read_header(path)
    except Exception as e:
        print(f"  skip  {path.name}: cannot read header ({e})", file=sys.stderr)
        return

    if not is_wasim_grid(path, hdr):
        expected = HEADER_BYTES + hdr["ncols"] * hdr["nrows"] * FLOAT_SIZE
        actual = path.stat().st_size
        print(
            f"  skip  {path.name}: size mismatch (expected {expected}, got {actual})",
            file=sys.stderr,
        )
        return

    vrt_path = path.with_name(path.name + ".vrt")
    vrt_path.write_text(make_vrt(path, hdr, crs))
    print(
        f"  wrote {vrt_path.name}  "
        f"({hdr['ncols']}x{hdr['nrows']}, cell={hdr['cellsize']:.0f}m, "
        f"ll=({hdr['xllcorner']:.0f}, {hdr['yllcorner']:.0f}))"
    )


def main() -> None:
    args = sys.argv[1:]
    crs = DEFAULT_CRS
    paths = []

    # minimal arg parsing: --crs EPSG:XXXX
    i = 0
    while i < len(args):
        if args[i] == "--crs" and i + 1 < len(args):
            crs = args[i + 1]
            i += 2
        else:
            paths.append(Path(args[i]))
            i += 1

    if not paths:
        print(__doc__)
        sys.exit(1)

    print(f"CRS: {crs}")
    for p in paths:
        if not p.is_file():
            print(f"  skip  {p}: not a file", file=sys.stderr)
            continue
        if p.suffix == ".vrt":
            print(f"  skip  {p.name}: already a VRT", file=sys.stderr)
            continue
        process(p, crs)


if __name__ == "__main__":
    main()
