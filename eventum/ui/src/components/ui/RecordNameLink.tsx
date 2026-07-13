import { Anchor } from '@mantine/core';
import { FC, MouseEvent, ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface RecordNameLinkProps {
  to: string;
  children: ReactNode;
}

// Cancel navigation when the click ends a text selection inside the link,
// so the name stays copyable without opening the record.
function handleClick(event: MouseEvent<HTMLAnchorElement>) {
  const selection = globalThis.getSelection();
  if (
    selection &&
    !selection.isCollapsed &&
    event.currentTarget.contains(selection.anchorNode)
  ) {
    event.preventDefault();
  }
}

/**
 * Record name rendered as a real link to the record's page.
 *
 * Left click opens the record; middle or modifier click opens it in a
 * new browser tab (native anchor behavior). Selecting the name text does
 * not navigate, so the name stays copyable.
 */
export const RecordNameLink: FC<RecordNameLinkProps> = ({ to, children }) => {
  return (
    <Anchor
      component={Link}
      to={to}
      onClick={handleClick}
      c="inherit"
      fz="inherit"
      underline="never"
      style={{ userSelect: 'text' }}
    >
      {children}
    </Anchor>
  );
};
