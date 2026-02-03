import { ItemInstance } from '@headless-tree/core';
import { Flex } from '@mantine/core';
import {
  IconBraces,
  IconBrandPython,
  IconCube,
  IconFileInvoice,
  IconFileSpreadsheet,
  IconFileText,
  IconFolder,
  IconMarkdown,
} from '@tabler/icons-react';
import { FC } from 'react';

import { FileNode } from '@/api/routes/generator-configs/schemas';
import { IconJinja } from '@/components/ui/icons/IconJinja';

interface FileNodeItemIconProps {
  item: ItemInstance<FileNode>;
}

export const FileNodeItemIcon: FC<FileNodeItemIconProps> = ({ item }) => {
  const size = 15;

  if (item.isFolder()) {
    return (
      <Flex align="center">
        <IconFolder size={size} />
      </Flex>
    );
  }

  const fileName = item.getItemName();
  if (/^generator\.ya?ml$/.test(fileName)) {
    return (
      <Flex c="primary" align="center">
        <IconCube size={size} />
      </Flex>
    );
  }
  if (fileName.endsWith('.py')) {
    return (
      <Flex c="blue" align="center">
        <IconBrandPython size={size} />
      </Flex>
    );
  }
  if (fileName.endsWith('.jinja')) {
    return (
      <Flex c="gray.6">
        <IconJinja size={size} />
      </Flex>
    );
  }
  if (fileName.endsWith('.csv') || fileName.endsWith('.tsv')) {
    return (
      <Flex c="green" align="center">
        <IconFileSpreadsheet size={size} />
      </Flex>
    );
  }
  if (fileName.endsWith('.json')) {
    return (
      <Flex c="orange" align="center">
        <IconBraces size={size} />
      </Flex>
    );
  }
  if (fileName.endsWith('.yml') || fileName.endsWith('.yaml')) {
    return (
      <Flex c="red" align="center">
        <IconFileInvoice size={size} />
      </Flex>
    );
  }
  if (fileName.endsWith('.md')) {
    return (
      <Flex c="blue" align="center">
        <IconMarkdown size={size} />
      </Flex>
    );
  }

  return (
    <Flex align="center">
      <IconFileText size={size} />
    </Flex>
  );
};
