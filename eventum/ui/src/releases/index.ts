import { FC } from 'react';

import {
  DiscoverScene,
  GlobalStateScene,
  InstanceResourcesScene,
  KeyringPickerScene,
  LogChannelsScene,
  MonitoringScene,
  OpeningScene,
  ProjectArchiveScene,
  QueueBytesScene,
  RepositoriesScene,
} from './illustrations/scenes';
import { compareVersions } from '@/utils/version';

/**
 * What every release brought, as Studio tells it.
 *
 * The panels are curated per release and shipped inside the build: an
 * instance with no outbound access shows them the same way one with a
 * connection does. The full list of changes stays where it was, on the
 * changelog page each entry links to.
 */

export interface ReleaseHighlight {
  /** Identifies the panel; stable across releases it reappears in. */
  id: string;
  title: string;
  body: string;
  /** The animated illustration drawn above the text. */
  scene: FC;
  /** Where the change is documented in full. */
  docsHref?: string;
}

export interface Release {
  /** The version these panels describe, as `app_version` reports it. */
  version: string;
  changelogHref: string;
  highlights: ReleaseHighlight[];
}

const DOCS = 'https://eventum.run/docs';

/** Newest release first. */
export const RELEASES: Release[] = [
  {
    version: '2.8.0',
    changelogHref: `${DOCS}/changelog/2.8.0`,
    highlights: [
      {
        id: 'opening',
        title: 'What 2.8.0 brought',
        body: 'Ready-made generators, projects that travel, and what a run costs.',
        scene: OpeningScene,
      },
      {
        id: 'repositories',
        title: 'Generators arrive from a repository',
        body: 'Connect one and install what its catalog publishes.',
        scene: RepositoriesScene,
        docsHref: `${DOCS}/studio/repositories`,
      },
      {
        id: 'discover',
        title: 'Find a repository on GitHub',
        body: 'Search the ones carrying the eventum-generators topic.',
        scene: DiscoverScene,
        docsHref: `${DOCS}/studio/repositories#finding-a-repository`,
      },
      {
        id: 'project-archive',
        title: 'Projects travel as archives',
        body: 'Export one, import it on another instance.',
        scene: ProjectArchiveScene,
        docsHref: `${DOCS}/studio/projects#moving-a-project-between-instances`,
      },
      {
        id: 'keyring-picker',
        title: 'Pick a secret, not its name',
        body: 'Every password field offers what the keyring holds.',
        scene: KeyringPickerScene,
        docsHref: `${DOCS}/core/config/secrets`,
      },
      {
        id: 'global-state',
        title: 'Scripts share the global state',
        body: 'A script reaches the keys a template already writes.',
        scene: GlobalStateScene,
        docsHref: `${DOCS}/plugins/event/script`,
      },
      {
        id: 'monitoring',
        title: 'Monitoring points at the instance',
        body: 'Open the details of any row beside the table.',
        scene: MonitoringScene,
        docsHref: `${DOCS}/studio/monitoring`,
      },
      {
        id: 'instance-resources',
        title: 'See what each instance costs',
        body: 'Rank the running ones by what they occupy.',
        scene: InstanceResourcesScene,
        docsHref: `${DOCS}/studio/monitoring#instances`,
      },
      {
        id: 'log-channels',
        title: 'A log for every component',
        body: 'Switch channels on the Management page.',
        scene: LogChannelsScene,
        docsHref: `${DOCS}/studio/settings#management`,
      },
      {
        id: 'queue-bytes',
        title: 'The events queue is bounded',
        body: 'It stops at a size now, not at a count of batches.',
        scene: QueueBytesScene,
        docsHref: `${DOCS}/core/config/eventum-yml#generationqueue`,
      },
    ],
  },
];

/**
 * The release whose panels a given version of the application shows -
 * the newest one it has reached that describes anything. A patch release
 * carrying no panels of its own therefore still shows the ones of the
 * release it follows.
 */
export function pickRelease(
  appVersion: string,
  releases: Release[] = RELEASES
): Release | undefined {
  let picked: Release | undefined;

  for (const release of releases) {
    if (release.highlights.length === 0) {
      continue;
    }

    if (compareVersions(release.version, appVersion) > 0) {
      continue;
    }

    if (
      picked === undefined ||
      compareVersions(release.version, picked.version) > 0
    ) {
      picked = release;
    }
  }

  return picked;
}
