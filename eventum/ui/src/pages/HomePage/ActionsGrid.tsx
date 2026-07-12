import { Group, Paper, SimpleGrid, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconFolder,
  IconPlayerPlay,
  IconPlus,
  IconSearch,
  IconTransform,
} from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { Link, generatePath, useNavigate } from 'react-router-dom';

import { CreateProjectModal } from '@/pages/ProjectsPage/CreateProjectModal';
import { ROUTE_PATHS } from '@/routing/paths';

interface ActionCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  onClick?: () => void;
  href?: string;
  to?: string;
}

const iconProps = {
  size: 22,
  color: 'var(--mantine-primary-color-filled)',
  stroke: 1.5,
  style: { flexShrink: 0 },
} as const;

const cardHoverStyles = {
  root: {
    '&:hover': {
      borderColor: 'var(--mantine-primary-color-filled)',
    },
  },
} as const;

const ActionCard: FC<ActionCardProps> = ({
  icon,
  title,
  description,
  onClick,
  href,
  to,
}) => {
  const content = (
    <Stack gap="sm">
      <Group gap="sm" wrap="nowrap">
        {icon}
        <Text size="sm" fw={600}>
          {title}
        </Text>
      </Group>
      <Text size="sm" c="dimmed" lh={1.5}>
        {description}
      </Text>
    </Stack>
  );

  const baseStyle = {
    cursor: 'pointer',
    transition: 'border-color 150ms ease',
  };
  const linkStyle = {
    ...baseStyle,
    textDecoration: 'none',
    color: 'inherit',
  };

  if (to !== undefined) {
    return (
      <Paper
        withBorder
        p="lg"
        radius="md"
        h="100%"
        style={linkStyle}
        styles={cardHoverStyles}
        component={Link}
        to={to}
      >
        {content}
      </Paper>
    );
  }

  if (href !== undefined) {
    return (
      <Paper
        withBorder
        p="lg"
        radius="md"
        h="100%"
        style={linkStyle}
        styles={cardHoverStyles}
        component="a"
        href={href}
        target="_blank"
        rel="noopener noreferrer"
      >
        {content}
      </Paper>
    );
  }

  return (
    <Paper
      withBorder
      p="lg"
      radius="md"
      h="100%"
      style={baseStyle}
      styles={cardHoverStyles}
      onClick={onClick}
    >
      {content}
    </Paper>
  );
};

interface ActionsGridProps {
  existingProjectNames: string[];
}

export const ActionsGrid: FC<ActionsGridProps> = ({ existingProjectNames }) => {
  const navigate = useNavigate();

  return (
    <Stack gap="lg">
      {/* Row 1: 2 cards at 50% */}
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <ActionCard
          icon={<IconPlus {...iconProps} />}
          title="New Project"
          description="Start from scratch — pick an event plugin, set up scheduling, and configure where your synthetic data goes."
          onClick={() =>
            modals.open({
              title: 'New project',
              children: (
                <CreateProjectModal
                  existingProjectNames={existingProjectNames}
                  onCreated={(name) =>
                    void navigate(
                      generatePath(ROUTE_PATHS.PROJECT, {
                        projectName: name,
                      })
                    )
                  }
                />
              ),
              size: 'lg',
            })
          }
        />
        <ActionCard
          icon={<IconSearch {...iconProps} />}
          title="Browse Eventum Hub"
          description="Explore ready-to-use generators for popular data sources — deploy production-grade synthetic events in seconds."
          href="https://eventum.run/hub"
        />
      </SimpleGrid>

      {/* Row 2: 3 cards at 33% */}
      <SimpleGrid cols={{ base: 1, xs: 2, sm: 3 }} spacing="md">
        <ActionCard
          icon={<IconFolder {...iconProps} />}
          title="Projects"
          description="All your generator projects in one place. Open any project to visually design its complete plugin pipeline."
          to={ROUTE_PATHS.PROJECTS}
        />
        <ActionCard
          icon={<IconPlayerPlay {...iconProps} />}
          title="Instances"
          description="See what's running right now. Each instance shows live performance metrics, structured logs, and full lifecycle controls."
          to={ROUTE_PATHS.INSTANCES}
        />
        <ActionCard
          icon={<IconTransform {...iconProps} />}
          title="Scenarios"
          description="Orchestrate multi-generator workflows — coordinate instances with global state and unified lifecycle controls."
          to={ROUTE_PATHS.SCENARIOS}
        />
      </SimpleGrid>
    </Stack>
  );
};
