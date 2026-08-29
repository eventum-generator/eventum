import {
  ActionIcon,
  Anchor,
  Button,
  CloseButton,
  Group,
  Modal,
  Text,
  Title,
} from '@mantine/core';
import { IconArrowLeft, IconArrowRight } from '@tabler/icons-react';
import { FC, PointerEvent, useCallback, useEffect, useState } from 'react';

import './reel.css';
import { Release } from '@/releases';

/** How far a finger has to travel across a panel to page it. */
const SWIPE_THRESHOLD = 48;

/** The finger a swipe is being followed on, and where it went down. */
interface Swipe {
  pointerId: number;
  x: number;
}

interface ReelProps {
  release: Release;
  opened: boolean;
  onClose: () => void;
}

/**
 * The release panels, one at a time.
 *
 * A panel is a scene of the feature being used, a title and one line -
 * the scene explains, the line names. Paging is by button, by the dots,
 * by swipe or by arrow key; Escape leaves at any point, and the last
 * panel hands over to the full changelog.
 */
const Reel: FC<ReelProps> = ({ release, opened, onClose }) => {
  const panels = release.highlights;
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<'forward' | 'back'>('forward');
  const [swipe, setSwipe] = useState<Swipe | null>(null);

  const isLast = index === panels.length - 1;

  // The ends hold: an arrow pressed there neither moves the reel nor
  // replays the entrance of the panel already on screen.
  const goTo = useCallback(
    (position: number) => {
      const next = Math.max(0, Math.min(panels.length - 1, position));

      if (next === index) {
        return;
      }

      setDirection(next > index ? 'forward' : 'back');
      setIndex(next);
    },
    [index, panels.length]
  );

  const back = useCallback(() => goTo(index - 1), [goTo, index]);
  const forward = useCallback(() => goTo(index + 1), [goTo, index]);

  // A reel is watched from its start every time it is opened.
  useEffect(() => {
    if (opened) {
      setIndex(0);
      setDirection('forward');
    }
  }, [opened]);

  useEffect(() => {
    if (!opened) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      // A modified arrow belongs to whoever is selecting text or driving
      // a screen reader with it.
      if (
        event.defaultPrevented ||
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey
      ) {
        return;
      }

      if (event.key === 'ArrowRight') {
        forward();
      } else if (event.key === 'ArrowLeft') {
        back();
      }
    };

    globalThis.addEventListener('keydown', onKeyDown);

    return () => globalThis.removeEventListener('keydown', onKeyDown);
  }, [opened, forward, back]);

  // Only a finger or a pen swipes: a mouse drag across a panel is a
  // reader selecting the text of it, not asking for the next one. The
  // pointer is followed by its id, so a second finger cannot end the
  // gesture the first one started.
  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    setSwipe(
      event.pointerType === 'mouse'
        ? null
        : { pointerId: event.pointerId, x: event.clientX }
    );
  };

  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (swipe?.pointerId !== event.pointerId) {
      return;
    }

    const travelled = event.clientX - swipe.x;
    setSwipe(null);

    if (travelled <= -SWIPE_THRESHOLD) {
      forward();
    } else if (travelled >= SWIPE_THRESHOLD) {
      back();
    }
  };

  // Clamped again here: a release replaced under an open reel - an
  // instance upgraded in another tab - can carry fewer panels than the
  // one being read.
  const panel = panels[Math.min(index, panels.length - 1)];

  if (panel === undefined) {
    return null;
  }

  const Illustration = panel.scene;

  return (
    // Composed rather than the plain `Modal`, because only `Modal.Content`
    // carries the dialog role and can therefore be given its name. The
    // theme's Modal defaults do not reach the composed parts, so the
    // house radius and centring are repeated here.
    <Modal.Root
      opened={opened}
      onClose={onClose}
      size={520}
      padding={0}
      radius="lg"
      centered
      transitionProps={{ transition: 'fade', duration: 320, exitDuration: 120 }}
    >
      <Modal.Overlay blur={8} backgroundOpacity={0.7} />
      <Modal.Content
        classNames={{ content: 'ev-reel' }}
        aria-label="What's new in Eventum"
      >
        <div
          className="ev-reel-stage"
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
        >
          <div key={panel.id} className="ev-reel-scene" data-way={direction}>
            <Illustration />
          </div>

          <span className="ev-reel-glow" aria-hidden="true" />
          <span className="ev-reel-sweep" aria-hidden="true" />

          <span className="ev-reel-badge">
            What&apos;s new
            <span className="ev-reel-version">{release.version}</span>
          </span>

          <CloseButton
            className="ev-reel-close"
            size="md"
            radius="xl"
            onClick={onClose}
            aria-label="Close"
          />
        </div>

        <div
          className="ev-reel-copy"
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
        >
          <div key={panel.id} className="ev-reel-words" data-way={direction}>
            <Title order={2} fz="xl" lh={1.25}>
              {panel.title}
            </Title>
            <Text c="dimmed" mt={6}>
              {panel.body}
            </Text>
            {panel.docsHref !== undefined && (
              <Anchor
                href={panel.docsHref}
                target="_blank"
                rel="noreferrer"
                fz="sm"
                mt="xs"
                display="inline-block"
              >
                Learn more
              </Anchor>
            )}
          </div>
        </div>

        <Group
          className="ev-reel-controls"
          justify="space-between"
          align="center"
          px="lg"
          pb="lg"
          pt="xs"
          wrap="nowrap"
        >
          <div
            className="ev-reel-dots"
            role="progressbar"
            aria-label="Release panels"
            aria-valuemin={1}
            aria-valuemax={panels.length}
            aria-valuenow={index + 1}
          >
            {panels.map((each, position) => (
              <button
                key={each.id}
                type="button"
                className="ev-reel-dot"
                data-current={position === index}
                aria-label={`Panel ${position + 1}`}
                onClick={() => goTo(position)}
              />
            ))}
          </div>

          <Group gap="xs" wrap="nowrap">
            {isLast && (
              <Anchor
                href={release.changelogHref}
                target="_blank"
                rel="noreferrer"
                fz="sm"
                c="dimmed"
                mr="xs"
              >
                Full changelog
              </Anchor>
            )}
            <ActionIcon
              variant="subtle"
              color="gray"
              size="lg"
              radius="xl"
              onClick={back}
              disabled={index === 0}
              aria-label="Back"
            >
              <IconArrowLeft size={18} />
            </ActionIcon>
            <Button
              radius="xl"
              px="lg"
              onClick={isLast ? onClose : forward}
              rightSection={isLast ? undefined : <IconArrowRight size={16} />}
            >
              {isLast ? 'Done' : 'Next'}
            </Button>
          </Group>
        </Group>
      </Modal.Content>
    </Modal.Root>
  );
};

interface ReleaseHighlightsModalProps {
  /** Nothing is drawn for an instance with no panels to show. */
  release: Release | undefined;
  opened: boolean;
  onClose: () => void;
}

export const ReleaseHighlightsModal: FC<ReleaseHighlightsModalProps> = ({
  release,
  opened,
  onClose,
}) => {
  if (release === undefined || release.highlights.length === 0) {
    return null;
  }

  return <Reel release={release} opened={opened} onClose={onClose} />;
};
