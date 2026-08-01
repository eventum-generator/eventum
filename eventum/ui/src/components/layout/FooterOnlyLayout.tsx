import { Anchor, AppShell, Group, Text } from '@mantine/core';

import { LINKS } from '@/routing/links';

export default function FooterOnlyLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const data = [
    {
      label: 'Documentation',
      link: LINKS.DOCUMENTATION,
    },
    {
      label: 'GitHub',
      link: LINKS.GITHUB_ORGANIZATION,
    },
    {
      label: 'Community',
      link: LINKS.GITHUB_DISCUSSIONS,
    },
  ];
  return (
    <AppShell>
      <AppShell.Main>{children}</AppShell.Main>
      {/* The page under this layout is bare canvas, so the footer sits on the
          canvas colour too - AppShell paints its sections the panel colour,
          which would draw a lighter strip across the bottom. */}
      <AppShell.Footer bd="0" bg="var(--ev-canvas)">
        <Group justify="space-between" mx="50px" my="20px">
          <Text c="dimmed" size="sm">
            © {new Date().getFullYear()} Eventum Generator.{' '}
            <Anchor
              href={LINKS.LICENSE}
              c="dimmed"
              lh={1}
              size="sm"
              target="_blank"
            >
              All rights reserved.
            </Anchor>
          </Text>

          <Group gap="lg">
            {data.map((element) => (
              <Anchor
                key={element.label}
                href={element.link}
                c="dimmed"
                lh={1}
                size="sm"
                target="_blank"
              >
                {element.label}
              </Anchor>
            ))}
          </Group>
        </Group>
      </AppShell.Footer>
    </AppShell>
  );
}
