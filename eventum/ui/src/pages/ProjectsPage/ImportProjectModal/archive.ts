/**
 * Reading the entry names of a ZIP archive in the browser.
 *
 * Only the names are needed - to propose a project name that matches
 * the directory the archive carries - so the file is not decompressed.
 * The central directory holds every name in plain form at the tail of
 * the archive, and that is the only part read.
 */

// Record signatures, as the little-endian words they are read as:
// 'PK\x05\x06' ends the central directory, 'PK\x01\x02' starts an entry
// in it.
const END_OF_CENTRAL_DIRECTORY_SIGNATURE = 101_010_256;
const CENTRAL_DIRECTORY_ENTRY_SIGNATURE = 33_639_248;

// The end-of-central-directory record is 22 bytes plus a comment of at
// most 64 KiB, so it always begins within this many bytes of the end.
const END_OF_CENTRAL_DIRECTORY_MAX_OFFSET = 22 + 65_535;

const CENTRAL_DIRECTORY_ENTRY_HEADER_SIZE = 46;

async function readTail(file: File, length: number): Promise<DataView> {
  const start = Math.max(0, file.size - length);
  const buffer = await file.slice(start).arrayBuffer();

  return new DataView(buffer);
}

/** Offset of the end-of-central-directory record within the tail. */
function findEndOfCentralDirectory(tail: DataView): number | null {
  for (let offset = tail.byteLength - 22; offset >= 0; offset -= 1) {
    if (tail.getUint32(offset, true) === END_OF_CENTRAL_DIRECTORY_SIGNATURE) {
      return offset;
    }
  }

  return null;
}

function parseEntryNames(directory: DataView, count: number): string[] {
  const decoder = new TextDecoder();
  const names: string[] = [];
  let offset = 0;

  for (let index = 0; index < count; index += 1) {
    if (offset + CENTRAL_DIRECTORY_ENTRY_HEADER_SIZE > directory.byteLength) {
      break;
    }

    if (
      directory.getUint32(offset, true) !== CENTRAL_DIRECTORY_ENTRY_SIGNATURE
    ) {
      break;
    }

    const nameLength = directory.getUint16(offset + 28, true);
    const extraLength = directory.getUint16(offset + 30, true);
    const commentLength = directory.getUint16(offset + 32, true);
    const nameStart = offset + CENTRAL_DIRECTORY_ENTRY_HEADER_SIZE;

    names.push(
      decoder.decode(
        new Uint8Array(
          directory.buffer,
          directory.byteOffset + nameStart,
          nameLength
        )
      )
    );

    offset = nameStart + nameLength + extraLength + commentLength;
  }

  return names;
}

/**
 * Entry names of a ZIP archive, or an empty list when the file is not
 * one Eventum can read here.
 *
 * A file this fails on is not rejected: the backend is what validates
 * an archive, and the name proposal falls back to the file name.
 */
export async function readZipEntryNames(file: File): Promise<string[]> {
  try {
    const tail = await readTail(file, END_OF_CENTRAL_DIRECTORY_MAX_OFFSET);
    const end = findEndOfCentralDirectory(tail);

    if (end === null) return [];

    const count = tail.getUint16(end + 10, true);
    const size = tail.getUint32(end + 12, true);
    const start = tail.getUint32(end + 16, true);

    // A field left at its maximum means Zip64 keeps the real value
    // elsewhere; such an archive holds far more than a project, so it
    // is left to the backend.
    const zip64Marker = 4_294_967_295;

    if (start === zip64Marker || size === zip64Marker) return [];

    const directory = await file.slice(start, start + size).arrayBuffer();

    return parseEntryNames(new DataView(directory), count);
  } catch {
    return [];
  }
}

/**
 * Name of the directory the archive carries the project in, or `null`
 * when the archive holds it at the top level or is not a project.
 *
 * Mirrors how the backend finds the project root: the shallowest entry
 * named after the generator configuration marks it, and its parent
 * directory is the project. More than one at that depth means the
 * archive holds several projects, which the backend refuses.
 */
export function projectRootName(
  entryNames: string[],
  configFilename: string
): string | null {
  const suffix = `/${configFilename}`;
  const configs = entryNames.filter(
    (name) => name === configFilename || name.endsWith(suffix)
  );

  if (configs.length === 0) return null;

  const depth = Math.min(...configs.map((name) => name.split('/').length));
  const shallowest = configs.filter((name) => name.split('/').length === depth);

  if (shallowest.length > 1 || depth < 2) return null;

  return shallowest[0]?.split('/')[depth - 2] ?? null;
}
