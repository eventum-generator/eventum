import { Title } from '@mantine/core';
import { FC } from 'react';

interface PageTitleProps {
  title: string;
}

export const PageTitle: FC<PageTitleProps> = ({ title }) => {
  return (
    <Title order={2} fz="1.5rem" fw={650}>
      {title}
    </Title>
  );
};
