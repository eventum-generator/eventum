import { describe, expect, it } from 'vitest';

import { projectRootName, readZipEntryNames } from './archive';

// Real archives, built with a ZIP writer: 'web-nginx/generator.yml'
// plus a template, the same two at the top level, and a project three
// directories deep.
const NESTED_ARCHIVE =
  'UEsDBBQAAAAIADWpEl1+OOAcDAAAAAoAAAAXAAAAd2ViLW5naW54L2dlbmVyYXRvci55bWzLzCsoLbFSiI7lAgBQSwMEFAAAAAgANakSXUO/pqMEAAAAAgAAAB8AAAB3ZWItbmdpbngvdGVtcGxhdGVzL2V2ZW50Lmppbmphq64FAFBLAQIUAxQAAAAIADWpEl1+OOAcDAAAAAoAAAAXAAAAAAAAAAAAAACAAQAAAAB3ZWItbmdpbngvZ2VuZXJhdG9yLnltbFBLAQIUAxQAAAAIADWpEl1Dv6ajBAAAAAIAAAAfAAAAAAAAAAAAAACAAUEAAAB3ZWItbmdpbngvdGVtcGxhdGVzL2V2ZW50LmppbmphUEsFBgAAAAACAAIAkgAAAIIAAAAAAA==';
const FLAT_ARCHIVE =
  'UEsDBBQAAAAIADWpEl1+OOAcDAAAAAoAAAANAAAAZ2VuZXJhdG9yLnltbMvMKygtsVKIjuUCAFBLAwQUAAAACAA1qRJdQ7+mowQAAAACAAAAFQAAAHRlbXBsYXRlcy9ldmVudC5qaW5qYauuBQBQSwECFAMUAAAACAA1qRJdfjjgHAwAAAAKAAAADQAAAAAAAAAAAAAAgAEAAAAAZ2VuZXJhdG9yLnltbFBLAQIUAxQAAAAIADWpEl1Dv6ajBAAAAAIAAAAVAAAAAAAAAAAAAACAATcAAAB0ZW1wbGF0ZXMvZXZlbnQuamluamFQSwUGAAAAAAIAAgB+AAAAbgAAAAAA';
const DEEP_ARCHIVE =
  'UEsDBBQAAAAIADWpEl1+OOAcDAAAAAoAAAAzAAAAY29udGVudC1wYWNrcy9nZW5lcmF0b3JzL2xpbnV4LWF1ZGl0ZC9nZW5lcmF0b3IueW1sy8wrKC2xUoiO5QIAUEsBAhQDFAAAAAgANakSXX444BwMAAAACgAAADMAAAAAAAAAAAAAAIABAAAAAGNvbnRlbnQtcGFja3MvZ2VuZXJhdG9ycy9saW51eC1hdWRpdGQvZ2VuZXJhdG9yLnltbFBLBQYAAAAAAQABAGEAAABdAAAAAAA=';

function archiveFile(base64: string, name = 'archive.zip'): File {
  const bytes = Uint8Array.from(
    atob(base64),
    (char) => char.codePointAt(0) ?? 0
  );

  return new File([bytes], name, { type: 'application/zip' });
}

describe('readZipEntryNames', () => {
  it('reads the entry names of an archive', async () => {
    const names = await readZipEntryNames(archiveFile(NESTED_ARCHIVE));

    expect(names).toEqual([
      'web-nginx/generator.yml',
      'web-nginx/templates/event.jinja',
    ]);
  });

  it('returns nothing for a file that is not an archive', async () => {
    const file = new File(['not an archive'], 'archive.zip');

    expect(await readZipEntryNames(file)).toEqual([]);
  });

  it('returns nothing for an empty file', async () => {
    expect(await readZipEntryNames(new File([], 'archive.zip'))).toEqual([]);
  });
});

describe('projectRootName', () => {
  it('names the directory holding the project', async () => {
    const names = await readZipEntryNames(archiveFile(NESTED_ARCHIVE));

    expect(projectRootName(names, 'generator.yml')).toBe('web-nginx');
  });

  it('names the deepest directory of a nested project', async () => {
    const names = await readZipEntryNames(archiveFile(DEEP_ARCHIVE));

    expect(projectRootName(names, 'generator.yml')).toBe('linux-auditd');
  });

  it('has no name for a project at the top level', async () => {
    const names = await readZipEntryNames(archiveFile(FLAT_ARCHIVE));

    expect(projectRootName(names, 'generator.yml')).toBeNull();
  });

  it('has no name when the archive holds no configuration', () => {
    expect(
      projectRootName(['a/templates/event.jinja'], 'generator.yml')
    ).toBeNull();
  });

  it('has no name when the archive holds several projects', () => {
    const names = ['first/generator.yml', 'second/generator.yml'];

    expect(projectRootName(names, 'generator.yml')).toBeNull();
  });

  it('takes the shallowest configuration', () => {
    const names = ['web/generator.yml', 'web/nested/generator.yml'];

    expect(projectRootName(names, 'generator.yml')).toBe('web');
  });

  it('ignores a directory entry with the same ending', () => {
    const names = ['web/generator.yml/', 'other/generator.yml'];

    expect(projectRootName(names, 'generator.yml')).toBe('other');
  });
});
