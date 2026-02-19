import { FileNode } from '../../schemas';

export function flattenFileTree(
  fileTree: FileNode[],
  filesOnly: boolean
): string[] {
  const result: string[] = [];

  function traverse(node: FileNode, path: string) {
    const currentPath = path.length > 0 ? `${path}/${node.name}` : node.name;

    if (node.is_dir) {
      if (!filesOnly) {
        result.push(currentPath);
      }

      if (node.children) {
        // sort children before traversing
        const sortedChildren = [...node.children].sort((a, b) => {
          // folders first
          if (a.is_dir !== b.is_dir) {
            return a.is_dir ? -1 : 1;
          }

          // alphabetical
          return a.name.localeCompare(b.name, undefined, {
            sensitivity: 'base',
          });
        });

        for (const child of sortedChildren) {
          traverse(child, currentPath);
        }
      }
    } else {
      result.push(currentPath);
    }
  }

  // sort root level
  const sortedRoot = [...fileTree].sort((a, b) => {
    if (a.is_dir !== b.is_dir) {
      return a.is_dir ? -1 : 1;
    }

    return a.name.localeCompare(b.name, undefined, {
      sensitivity: 'base',
    });
  });

  for (const node of sortedRoot) {
    traverse(node, '');
  }

  return result;
}

export function createFileTreeLookup(fileTree: FileNode[]) {
  const items = new Map<string, FileNode>();
  const children = new Map<string, string[]>();

  children.set('', []);

  function traverse(node: FileNode, parentPath: string) {
    const currentPath =
      parentPath.length > 0 ? `${parentPath}/${node.name}` : node.name;

    items.set(currentPath, node);

    if (!children.has(parentPath)) {
      children.set(parentPath, []);
    }

    children.get(parentPath)!.push(currentPath);

    if (node.is_dir) {
      children.set(currentPath, []);

      if (node.children) {
        for (const child of node.children) {
          traverse(child, currentPath);
        }
      }
    }
  }

  for (const node of fileTree) {
    traverse(node, '');
  }

  // sort every directory
  for (const [, childIds] of children) {
    childIds.sort((a, b) => {
      const itemA = items.get(a)!;
      const itemB = items.get(b)!;

      // folders first
      if (itemA.is_dir !== itemB.is_dir) {
        return itemA.is_dir ? -1 : 1;
      }

      // alphabetical
      return itemA.name.localeCompare(itemB.name, undefined, {
        sensitivity: 'base',
      });
    });
  }

  return { items, children };
}
