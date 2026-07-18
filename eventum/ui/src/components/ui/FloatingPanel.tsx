import { Box, Transition } from '@mantine/core';
import { FC, ReactNode } from 'react';

interface FloatingPanelProps {
  mounted: boolean;
  children: ReactNode;
}

export const FloatingPanel: FC<FloatingPanelProps> = ({
  mounted,
  children,
}) => {
  return (
    <Transition
      mounted={mounted}
      transition="slide-up"
      duration={200}
      timingFunction="ease"
    >
      {(transitionStyle) => (
        <Box
          pos="sticky"
          bottom={10}
          h={60}
          w="100%"
          bdrs="md"
          display="flex"
          mt="xl"
          bg="var(--mantine-color-default)"
          style={{
            boxShadow: 'var(--ev-shadow)',
            border: '1px solid',
            borderColor: 'var(--mantine-color-default-border)',
            zIndex: 100,
            ...transitionStyle,
          }}
        >
          {children}
        </Box>
      )}
    </Transition>
  );
};
