import { FC } from 'react';

import {
  InstanceResourcesScene,
  LogChannelsScene,
  MonitoringScene,
  ProjectArchiveScene,
  QueueBytesScene,
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
        id: 'monitoring',
        title: 'Monitoring points at the instance',
        body: 'Open the details of any row beside the table.',
        scene: MonitoringScene,
        docsHref: `${DOCS}/studio/monitoring`,
      },
      {
        id: 'project-archive',
        title: 'Projects travel as archives',
        body: 'Export one, import it on another instance.',
        scene: ProjectArchiveScene,
        docsHref: `${DOCS}/studio/projects`,
      },
      {
        id: 'log-channels',
        title: 'A log for every component',
        body: 'Switch channels in the log viewer of an instance.',
        scene: LogChannelsScene,
        docsHref: `${DOCS}/core/config/eventum-yml`,
      },
      {
        id: 'queue-bytes',
        title: 'The events queue is bounded',
        body: 'It stops at a size now, not at a count of batches.',
        scene: QueueBytesScene,
        docsHref: `${DOCS}/core/config/eventum-yml`,
      },
      {
        id: 'instance-resources',
        title: 'See what each instance costs',
        body: 'Rank the running ones by what they occupy.',
        scene: InstanceResourcesScene,
        docsHref: `${DOCS}/studio/monitoring`,
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
