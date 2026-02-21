import { Completion } from '@codemirror/autocomplete';

interface NamespaceMember {
  completion: Completion;
  members?: Record<string, NamespaceMember>;
}

const templateStateCompletionMembers: Record<string, NamespaceMember> = {
  get: {
    completion: {
      label: 'get',
      type: 'function',
      detail: 'Get value from state',
      info: '(key: str, default: Any = None) -> Any',
    },
  },
  set: {
    completion: {
      label: 'set',
      type: 'function',
      detail: 'Set value to state',
      info: '(key: str, value: Any) -> None',
    },
  },
  update: {
    completion: {
      label: 'update',
      type: 'function',
      detail: 'Update state with new values',
      info: '(m: dict[str, Any]) -> None',
    },
  },
  clear: {
    completion: {
      label: 'clear',
      type: 'function',
      detail: 'Clear state',
      info: '() -> None',
    },
  },
  as_dict: {
    completion: {
      label: 'as_dict',
      type: 'function',
      detail: 'Get dictionary representation of state',
      info: '() -> dict[str, Any]',
    },
  },
};

const templateGlobalStateCompletionMembers: Record<string, NamespaceMember> = {
  ...templateStateCompletionMembers,
  acquire: {
    completion: {
      label: 'acquire',
      type: 'function',
      detail: 'Acquire state lock',
      info: '() -> None',
    },
  },
  release: {
    completion: {
      label: 'release',
      type: 'function',
      detail: 'Release state lock',
      info: '() -> None',
    },
  },
};

const namespaceCompletions: NamespaceMember = {
  completion: {
    label: '#',
    type: 'namespace',
    detail: 'Global',
  },
  members: {
    timestamp: {
      completion: {
        label: 'timestamp',
        type: 'variable',
        detail: 'Timestamp of the event',
        info: 'datetime',
      },
    },
    tags: {
      completion: {
        label: 'tags',
        type: 'variable',
        detail: 'Tags of input plugin that caused event',
        info: 'list[str]',
      },
    },
    params: {
      completion: {
        label: 'params',
        type: 'namespace',
        detail: 'Parameters provided in plugin configuration',
      },
    },
    samples: {
      completion: {
        label: 'samples',
        type: 'namespace',
        detail: 'Samples provided in plugin configuration',
      },
    },
    module: {
      completion: {
        label: 'module',
        type: 'namespace',
        detail: 'External modules',
      },
      members: {
        faker: {
          completion: {
            label: 'faker',
            type: 'namespace',
            detail: 'Module providing `Faker` library',
          },
          members: {
            locale: {
              completion: {
                label: 'locale',
                type: 'namespace',
                detail: 'Faker instances of specific locales',
              },
            },
          },
        },
        mimesis: {
          completion: {
            label: 'mimesis',
            type: 'namespace',
            detail: 'Module providing `Mimesis` library',
          },
          members: {
            enums: {
              completion: {
                label: 'enums',
                type: 'namespace',
                detail: 'Module mimesis.enums',
              },
            },
            random: {
              completion: {
                label: 'random',
                type: 'namespace',
                detail: 'Module mimesis.random',
              },
            },
            locale: {
              completion: {
                label: 'locale',
                type: 'namespace',
                detail: 'Generics of specific locales',
              },
            },
            spec: {
              completion: {
                label: 'spec',
                type: 'namespace',
                detail: 'Spec providers',
              },
            },
          },
        },
        rand: {
          completion: {
            label: 'rand',
            type: 'namespace',
            detail: 'Module for generating random values',
          },
          members: {
            shuffle: {
              completion: {
                label: 'shuffle',
                type: 'function',
                detail: 'Shuffle sequence elements',
                info: '(items: Sequence[T]) -> list[T] | str',
              },
            },
            choice: {
              completion: {
                label: 'choice',
                type: 'function',
                detail: 'Return random item from non empty sequence',
                info: '(items: Sequence[T]) -> T',
              },
            },
            choices: {
              completion: {
                label: 'choices',
                type: 'function',
                detail: 'Return `n` random items from non empty sequence',
                info: '(items: Sequence[T], n: int) -> list[T]',
              },
            },
            weighted_choice: {
              completion: {
                label: 'weighted_choice',
                type: 'function',
                detail:
                  'Return random item with weighted probability. Accepts (items, weights) or a dict {item: weight}',
                info: '(items: Sequence[T] | dict[T, float], weights?: Sequence[float]) -> T',
              },
            },
            weighted_choices: {
              completion: {
                label: 'weighted_choices',
                type: 'function',
                detail:
                  'Return `n` random items with weighted probability. Accepts (items, weights, n) or (dict, n)',
                info: '(items: Sequence[T] | dict[T, float], weights: Sequence[float] | int, n?: int) -> list[T]',
              },
            },
            chance: {
              completion: {
                label: 'chance',
                type: 'function',
                detail:
                  'Return `True` with the given probability `prob` (0.0 to 1.0).',
                info: 'chance(prob: float) -> bool',
              },
            },

            number: {
              completion: {
                label: 'number',
                type: 'namespace',
                detail: 'Namespace for generating random numbers.',
              },
              members: {
                integer: {
                  completion: {
                    label: 'integer',
                    type: 'function',
                    detail: 'Return random integer in range [a, b]',
                    info: '(a: int, b: int) -> int',
                  },
                },
                floating: {
                  completion: {
                    label: 'floating',
                    type: 'function',
                    detail:
                      'Return random floating point number in range [a, b]',
                    info: '(a: float, b: float) -> float',
                  },
                },
                gauss: {
                  completion: {
                    label: 'gauss',
                    type: 'function',
                    detail:
                      'Return random floating point number with Gaussian distribution',
                    info: '(mu: float, sigma: float) -> float',
                  },
                },
              },
            },

            string: {
              completion: {
                label: 'string',
                type: 'namespace',
                detail: 'Namespace for generating random strings.',
              },
              members: {
                letters_lowercase: {
                  completion: {
                    label: 'letters_lowercase',
                    type: 'function',
                    detail:
                      'Return string of specified `size` that contains random ASCII lowercase letters',
                    info: '(size: int) -> str',
                  },
                },
                letters_uppercase: {
                  completion: {
                    label: 'letters_uppercase',
                    type: 'function',
                    detail:
                      'Return string of specified `size` that contains random ASCII uppercase letters',
                    info: '(size: int) -> str',
                  },
                },
                letters: {
                  completion: {
                    label: 'letters',
                    type: 'function',
                    detail:
                      'Return string of specified `size` that contains random ASCII letters',
                    info: '(size: int) -> str',
                  },
                },
                digits: {
                  completion: {
                    label: 'digits',
                    type: 'function',
                    detail:
                      'Return string of specified `size` that contains random digit characters',
                    info: '(size: int) -> str',
                  },
                },
                punctuation: {
                  completion: {
                    label: 'punctuation',
                    type: 'function',
                    detail:
                      'Return string of specified `size` that contains random ASCII punctuation characters',
                    info: '(size: int) -> str',
                  },
                },
                hex: {
                  completion: {
                    label: 'hex',
                    type: 'function',
                    detail:
                      'Return string of specified `size` that contains random hex characters',
                    info: '(size: int) -> str',
                  },
                },
              },
            },

            network: {
              completion: {
                label: 'network',
                type: 'namespace',
                detail: 'Namespace for generating random network entities',
              },
              members: {
                ip_v4: {
                  completion: {
                    label: 'ip_v4',
                    type: 'function',
                    detail: 'Return random IPv4 address',
                    info: '() -> str',
                  },
                },
                ip_v4_private_a: {
                  completion: {
                    label: 'ip_v4_private_a',
                    type: 'function',
                    detail: 'Return random private IPv4 address of Class A',
                    info: '() -> str',
                  },
                },
                ip_v4_private_b: {
                  completion: {
                    label: 'ip_v4_private_b',
                    type: 'function',
                    detail: 'Return random private IPv4 address of Class B',
                    info: '() -> str',
                  },
                },
                ip_v4_private_c: {
                  completion: {
                    label: 'ip_v4_private_c',
                    type: 'function',
                    detail: 'Return random private IPv4 address of Class C',
                    info: '() -> str',
                  },
                },
                ip_v4_public: {
                  completion: {
                    label: 'ip_v4_public',
                    type: 'function',
                    detail: 'Return random public IPv4 address',
                    info: '() -> str',
                  },
                },
                mac: {
                  completion: {
                    label: 'mac',
                    type: 'function',
                    detail: 'Return random MAC address',
                    info: '() -> str',
                  },
                },
              },
            },

            crypto: {
              completion: {
                label: 'crypto',
                type: 'namespace',
                detail:
                  'Namespace for generating random cryptographic entities',
              },
              members: {
                uuid4: {
                  completion: {
                    label: 'uuid4',
                    type: 'function',
                    detail: 'Return universally unique identifier of version 4',
                    info: '() -> str',
                  },
                },
                md5: {
                  completion: {
                    label: 'md5',
                    type: 'function',
                    detail: 'Return random MD5 hash',
                    info: '() -> str',
                  },
                },
                sha256: {
                  completion: {
                    label: 'sha256',
                    type: 'function',
                    detail: 'Return random SHA-256 hash',
                    info: '() -> str',
                  },
                },
              },
            },

            datetime: {
              completion: {
                label: 'datetime',
                type: 'namespace',
                detail: 'Namespace for generating random dates',
              },
              members: {
                timestamp: {
                  completion: {
                    label: 'timestamp',
                    type: 'function',
                    detail: 'Return random timestamp in range [start; end].',
                    info: '(start: datetime, end: datetime) -> datetime',
                  },
                },
              },
            },
          },
        },
      },
    },
    subprocess: {
      completion: {
        label: 'subprocess',
        type: 'namespace',
        detail: 'Subprocess runner',
      },
      members: {
        run: {
          completion: {
            label: 'run',
            type: 'function',
            detail: 'Run command in a subprocess',
            info: '(command: str, cwd: str | None = None, env: dict[str, Any] | None = None, timeout: float | None = None) -> SubprocessResult',
          },
        },
      },
    },
    locals: {
      completion: {
        label: 'locals',
        type: 'namespace',
        detail: 'Local state of template',
      },
      members: templateStateCompletionMembers,
    },
    shared: {
      completion: {
        label: 'shared',
        type: 'namespace',
        detail: 'Shared state of templates within generator',
      },
      members: templateStateCompletionMembers,
    },
    globals: {
      completion: {
        label: 'globals',
        type: 'namespace',
        detail: 'Global state of templates withing all generators',
      },
      members: templateGlobalStateCompletionMembers,
    },
  },
};

const completionCache = new Map<string, Completion[]>();

export function getCompletions(path: string[]): Completion[] {
  const cacheKey = path.join('.');
  const cached = completionCache.get(cacheKey);
  if (cached) return cached;

  let context = namespaceCompletions;

  for (const node of path) {
    const members = context.members;
    if (members === undefined) {
      break;
    }

    const drilledMember = members[node];
    if (drilledMember === undefined) {
      break;
    }

    context = drilledMember;
  }

  const result =
    context.members === undefined
      ? []
      : Object.values(context.members).map((item) => item.completion);

  completionCache.set(cacheKey, result);

  return result;
}
