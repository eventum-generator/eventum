import { Badge, Box, Breadcrumbs } from '@mantine/core';
import { IconChevronRight } from '@tabler/icons-react';
import { FC } from 'react';
import { useLocation } from 'react-router-dom';

export const AppBreadcrumbs: FC = () => {
  const location = useLocation();

  return (
    <Breadcrumbs
      separator={<IconChevronRight size={'16px'} />}
      separatorMargin="0"
    >
      {location.pathname
        .split('/')
        .slice(1)
        .map((item, index) => (
          <Box
            key={item}
            style={{
              cursor: 'pointer',
            }}
          >
            <Badge
              variant="light"
              radius="sm"
              style={{
                textTransform: index === 0 ? 'capitalize' : 'none',
              }}
            >
              {item === '' ? 'Overview' : decodeURIComponent(item)}
            </Badge>
          </Box>
        ))}
    </Breadcrumbs>
  );
};
