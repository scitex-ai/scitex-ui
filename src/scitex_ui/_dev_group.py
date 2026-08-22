"""§13 — scitex-ui's own `dev` group.

Operator directive (doctrine ``general/03_interface/02_cli/20_dev-commands.md``,
shipped with scitex-dev): every self-maintenance surface a package ships
mounts under ONE group name, ``dev``.

    A package's top-level CLI is its DOMAIN. Self-maintenance plumbing is
    housekeeping, and housekeeping belongs under `dev`.
    `scitex-ui --help` then reads as the tool, not the tool's own upkeep.

Of the six FIXED verbs (`daemon`, `cron`, `systemd`, `hooks`, `skills`,
`shell`), scitex-ui ships exactly ONE today: `skills`. The other five are
NOT invented here — a verb appears when its surface does (a seventh verb
is forbidden by the doctrine; the six are a closed set).

SPLIT BY DEPENDENCY: the group MOVE is unconditional — the local
`_skills` module is self-contained (no scitex-dev needed). Only the
Phase W ALIAS depends on `scitex_dev.ecosystem.deprecated_alias`, and
it is registered behind the same `try/except ImportError` pattern the
rest of `_cli.py` uses for optional scitex-dev surfaces. In a bare
install (no scitex-dev) the legacy top-level spelling is simply absent
— the same world where the shared `skills_click_group` is also absent.
The §13 audit only ever runs where scitex-dev itself is installed, so
the audit's escape-hatch metadata is present in every world where the
audit can see it.
"""

from __future__ import annotations

import click

from ._cli_help import cli_help, examples as _examples, spec_group

#: Root group's help-option settings, mirrored from `_cli.CONTEXT_SETTINGS`
#: (not imported: `_cli` imports THIS module at the bottom of its own body,
#: so a top-level `from ._cli import ...` would be circular). Keeps `-h`
#: working on `dev --help` regardless of click version defaults.
_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

#: The one command moving from top level into `dev`. Data rather than
#: code so the alias loop below cannot drift from the mount — the failure
#: that would leave a command mounted with no alias, resolving nowhere.
_MOVED = ("skills",)

#: The version the Phase W alias disappears in. Deliberately distant and
#: semantically meaningful: v1.0, the first stable major of scitex-ui
#: (currently 0.17.0). The old spelling lives in scripts, cron lines,
#: agent prompts and documentation across the fleet, and none of those
#: are greppable from this repository — same rationale as scitex-dev's
#: own `_ALIAS_REMOVE_IN` in `scitex_dev._cli._dev_group`.
_ALIAS_REMOVE_IN = "1.0"


def register_dev_group(main: click.Group) -> click.Group:
    """Mount ``dev`` on *main* and populate it with self-maintenance surfaces.

    Returns the group so the caller can pass it to
    :func:`install_dev_aliases` AFTER population is complete.
    """
    from ._skills import skills_group

    @main.group(
        "dev",
        invoke_without_command=True,
        context_settings=_CONTEXT_SETTINGS,
        **spec_group(
            cli_help(
                summary="Package self-maintenance (§13 canonical group).",
                description=(
                    "Self-maintenance surfaces mount under one canonical "
                    "`dev` group (doctrine 20_dev-commands.md): a package's "
                    "top-level CLI is its domain, and housekeeping belongs "
                    "under `dev`. Currently: skills. The six fixed verbs "
                    "(daemon / cron / systemd / hooks / skills / shell) "
                    "appear as their surfaces ship.",
                ),
                examples=_examples(
                    ("{prog} skills list", "what is bundled"),
                    ("{prog} skills get 01_installation", "read one"),
                ),
            ),
            command_categories=[("Self-maintenance", ["skills"])],
        ),
    )
    @click.pass_context
    def dev(ctx: click.Context) -> None:
        """Package self-maintenance (§13 canonical group).

        \b
        Currently: skills. The six fixed verbs (daemon / cron / systemd /
        hooks / skills / shell) appear here as their surfaces ship.

        \b
        Example:
          $ scitex-ui dev skills list
          $ scitex-ui dev skills get 01_installation
          $ scitex-ui dev skills install
        """
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    dev.add_command(skills_group, name="skills")
    return dev


def install_dev_aliases(main: click.Group, dev: click.Group) -> None:
    """Phase W warn-forward aliases for every command that moved.

    Called AFTER all registrars have populated ``dev``, because an alias
    must point at a command that exists — building it earlier would
    silently produce an alias to nothing.

    Not a courtesy. A CLI whose old spelling stops resolving breaks every
    script, cron line and agent prompt that used it, and none of those
    are greppable from this repository.
    """
    try:
        from scitex_dev.ecosystem import deprecated_alias
    except ImportError:
        # scitex-dev is an OPTIONAL dependency ([project.optional-dependencies]
        # `cli` in pyproject.toml). The group move stands on its own —
        # `scitex-ui dev skills` works either way — but without the shared
        # helper there is nothing to register the legacy top-level spelling
        # as a hidden warn-forward alias. That spelling is simply absent in
        # a bare install, exactly as the shared `skills_click_group` is
        # (same ImportError world). Return, don't raise: `pip install
        # scitex-ui` with no extras must keep working.
        return

    for name in _MOVED:
        command = dev.commands.get(name)
        if command is None:
            # Fail loud rather than skip: a missing command here means a
            # registrar did not run, and a silently-absent alias is
            # indistinguishable from a successful migration.
            raise RuntimeError(
                f"§13 dev-group migration: {name!r} is not mounted on `dev`, "
                "so its Phase W alias cannot be built. Fix the mount rather "
                "than dropping the alias, or the old `scitex-ui "
                f"{name}` spelling resolves nowhere."
            )
        alias = deprecated_alias(
            main,
            name,
            target=command,
            target_name=f"dev {name}",
            remove_in=_ALIAS_REMOVE_IN,
            phase="warn",
        )
        # The helper authors the alias's help text and offers no spec hook,
        # so the §4b spec is attached HERE: it documents the same contract
        # (hidden, forwards every argument, warns once per shell, removed
        # in v1.0) so the derived coverage walk over the live tree stays
        # total rather than exempting the alias by name.
        alias._help_spec = cli_help(
            summary=f"(deprecated) Forwards to `dev {name}`.",
            description=(
                f"Legacy top-level spelling kept as a hidden Phase W "
                f"warn-forward alias: every argument and option "
                f"re-dispatches to `dev {name}`, and a once-per-shell "
                f"deprecation warning goes to stderr. "
                f"Removed in v{_ALIAS_REMOVE_IN}."
            ),
        )


__all__ = [
    "install_dev_aliases",
    "register_dev_group",
]


# EOF
