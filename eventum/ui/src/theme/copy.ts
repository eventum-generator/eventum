import { Fragment, createElement } from 'react';

/** Wraps `value` in bold, framed by plain-text `prefix`/`suffix`. */
function emphasize(prefix: string, value: string, suffix: string) {
  return createElement(
    Fragment,
    null,
    prefix,
    createElement('b', null, value),
    suffix
  );
}

/**
 * Canonical copy for confirm/destructive dialogs
 * (`modals.openConfirmModal`) and the unsaved-changes prompts. Single
 * source of truth - dialogs import and render these, they never retype
 * the wording at the call site.
 *
 * `title`/`confirm`/`cancel` are plain strings for direct use as
 * `modals.openConfirmModal({ title, labels: { confirm, cancel } })`.
 * `body` is either the static dialog text, or - where the sentence
 * names something dynamic (a file path, an instance id, ...) - a
 * function taking that value and returning the rendered sentence with
 * the value emphasized, matching the dialogs' existing look.
 */
export const CONFIRM = {
  restartInstance: {
    title: 'Restarting instance',
    body: 'Instance will be restarted. Do you want to continue?',
    confirm: 'Restart',
    cancel: 'Cancel',
  },
  stopInstance: {
    title: 'Stopping instance',
    body: 'Instance will be stopped. Do you want to continue?',
    confirm: 'Stop',
    cancel: 'Cancel',
  },
  deleteSecret: {
    title: 'Deleting secret',
    body: (name: string) =>
      emphasize(
        'Secret ',
        name,
        ' will be deleted from keyring. Do you want to continue?'
      ),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  closeUnsavedFile: {
    title: 'Unsaved changes',
    body: (path: string) =>
      emphasize(
        'All unsaved changes in ',
        path,
        ' will be lost. Do you want to continue?'
      ),
    confirm: 'Continue',
    cancel: 'Cancel',
  },
  deleteFile: {
    title: 'Deleting file',
    body: (path: string) =>
      emphasize('File "', path, '" will be deleted. Do you want to continue?'),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  deleteSample: {
    title: 'Deleting sample',
    body: (name: string) =>
      emphasize('Sample ', name, ' will be deleted. Do you want to continue?'),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  deleteProject: {
    title: 'Deleting project',
    body: (name: string) =>
      emphasize('Project ', name, ' will be deleted. Do you want to continue?'),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  deleteInstances: {
    title: 'Deleting instances',
    body: (ids: string) =>
      emphasize(
        'Instance(s) ',
        ids,
        ' will be deleted. Do you want to continue?'
      ),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  deleteInstance: {
    title: 'Deleting instance',
    body: (id: string) =>
      emphasize('Instance ', id, ' will be deleted. Do you want to continue?'),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  deletePlugin: {
    title: 'Deleting plugin',
    body: (label: string) =>
      emphasize('Plugin ', label, ' will be deleted. Do you want to continue?'),
    confirm: 'Delete',
    cancel: 'Cancel',
  },
  /** `UnsavedChangesPrompt`'s page-leave guard - its own Stay/Leave
   *  buttons are a different convention from confirm/cancel and stay
   *  defined on the component. */
  unsavedChanges: {
    title: 'Unsaved changes',
    body: 'You have unsaved changes that will be lost. Leave this page anyway?',
  },
};
