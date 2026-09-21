{ pkgs, lib, config, inputs, ... }:
let
  uvicorn-run = pkgs.writeShellScriptBin "uvicorn-run" ''
    set -e
    cd ${config.devenv.root} && uvicorn langnet.asgi:app "$@"
  '';
in
{
  # https://devenv.sh/basics/

  # setting LD_LIBRARY_PATH for python - but may conflict with system libs (eg: devenv)
  # hence: inside the shell use `devenv-wrapped` to clear env LD path
  env.LD_LIBRARY_PATH= "${pkgs.stdenv.cc.cc.lib}/lib/:${pkgs.zlib}/lib";

  env.CUDA_VISIBLE_DEVICES = "";
  env.GIT_EXTERNAL_DIFF = "difft";

  # python is wanting to download and install tarballs into tempdirs
  
  # https://devenv.sh/packages/
  packages = [ 
    pkgs.git
    # pkgs.nodejs
    pkgs.difftastic
    pkgs.opencode

    pkgs.ripgrep
    pkgs.fzf
    pkgs.jq # for the chatbots

    pkgs.poppler-utils

    # useful language servers
    pkgs.python3Packages.python-lsp-server
    pkgs.python3Packages.jedi-language-server
    pkgs.python3Packages.ruff
    pkgs.ty
    # pkgs.nodePackages.vscode-langservers-extracted
    # pkgs.nil

    # some python utilities
    # pkgs.black
    # pkgs.pipx
 
    # pkgs.libeb
    # some libraries for cltk deps (numpy, scipy)
    pkgs.zlib
    pkgs.gcc
    # pkgs.libgcc
    pkgs.gnumake
    pkgs.duckdb
    pkgs.sqlite

    pkgs.nodejs

    pkgs.just
    pkgs.hl-log-viewer

    uvicorn-run
  ];

  # https://devenv.sh/languages/
  # languages.rust.enable = true;
  languages.c.enable = true;
  languages.python.enable = true;
  languages.python.package = pkgs.python311; # the version that currently works with CLTK
  languages.python.venv.enable = true;
  languages.python.venv.requirements = ./devenv.requirements.txt;

  # The spec-generated modules (query_spec, heritage_spec, ...) live in the
  # sibling langnet-spec clone (see langnet-tools clone.sh); the tests import
  # them directly (HOL-121). The repo root is on the path so tests/ resolves
  # as a namespace package (`from tests.claim_contract import ...`).
  # NOTE: the typing_extensions compliance shim is prepended in enterShell
  # (below) — devenv injects the profile's python site-packages ahead of
  # user env.PYTHONPATH, so only the last-written export wins the race
  # (PR #13 CI: nix typing-extensions 4.15.0 shadows anyio's PEP 661
  # `sentinel` import).
  env.PYTHONPATH = "${config.devenv.root}/../langnet-spec/generated/python:${config.devenv.root}:${config.devenv.root}/src";
  
  # languages.python.poetry.package = (pkgs.poetry.override { python3 = pkgs.python311; });
  # languages.python.poetry.enable = true;
  # languages.python.poetry.activate.enable = true;
  # languages.python.poetry.install.enable = false;

  # languages.python.poetry.enable = true;
  # languages.python.poetry.package = (pkgs.poetry.override { python3 = pkgs.python311; });
  # languages.python.poetry.activate.enable = true;

  languages.javascript.enable = true;
  # languages.javascript.npm.enable = true;
  languages.javascript.bun.enable = true;
  languages.typescript.enable = true;

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";
  # 
  # http://localhost:5000
  # processes.poe-dev.exec = "$HOME/.local/bin/poe dev";

  # http://localhost:5173
  # processes.vite-dev.exec = "npm run dev --prefix=$DEVENV_ROOT/src-web";

  # http://localhost:888 
  # processes.diogenes.exec = "cd deps/diogenes; devenv-wrapped shell ./server/diogenes-server.pl";

  # # http://localhost:8000
  # processes.gunicorn.exec = "$HOME/.local/bin/poe serve";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  # scripts.devenv-wrapped.exec = ''
  #   LD_LIBRARY_PATH= devenv $@
  # '';

  enterShell = ''
    mkdir -p "${config.devenv.root}/tmp";
    export TMP="${config.devenv.root}/tmp";
    export TMPDIR="${config.devenv.root}/tmp";
    export CODEGEN_PATH=$DEVENV_ROOT/vendor/langnet-spec/generated/python
    export PYTHONPATH=$DEVENV_ROOT/src:$DEVENV_ROOT/.justscripts:$CODEGEN_PATH:$PYTHONPATH
    export PATH=$PATH:$HOME/.local/bin
    # typing_extensions compliance shim (PR #13 CI): devenv injects the
    # profile's tool-tree site-packages (pylsp/jedi deps, py3.13-built) ahead
    # of the venv on PYTHONPATH; they ship typing-extensions 4.15.0, and anyio
    # imports the PEP 661 `sentinel` name that first ships in 4.16.0 — the
    # suite died at import time (ModuleImportFailure.test_asgi_server).
    # Provision a compliant copy into a state dir and prepend it: enterShell
    # is the last export before the command, so this entry wins the path race
    # in every interpreter started from the shell. Idempotent + self-healing;
    # a network-less pip failure is non-fatal (suite reports the gap itself).
    if [ ! -f "${config.devenv.root}/.devenv/state/python-overrides/typing_extensions.py" ]; then
      if [ -x .devenv/state/venv/bin/python ]; then
        .devenv/state/venv/bin/python -m pip install -q --target "${config.devenv.root}/.devenv/state/python-overrides" "typing_extensions>=4.16,<5.0" || true
      fi
    fi
    export PYTHONPATH="${config.devenv.root}/.devenv/state/python-overrides:$PYTHONPATH"
  '';

  # scripts.gunicorn-serve.exec = ''
  #   $HOME/.local/bin/poe serve
  # '';

  # scripts.jsbuild.exec = ''
  #   npm run build --prefix=$DEVENV_ROOT/src-web && cp -r $DEVENV_ROOT/src-web/dist/* $DEVENV_ROOT/webroot/
  # '';

  # https://devenv.sh/tasks/
  tasks = {
    # "langnet:setup".exec = "pipx install gunicorn poethepoet flask nose2 && ${pkgs.poetry}/bin/poetry install";
    # "langnet:setup".exec = "pipx install gunicorn poethepoet flask nose2 poetry";
    # "langnet:jsinstall".exec = "npm install --prefix=$DEVENV_ROOT/src-web";

    # "langnet:jsbuild".exec = "jsbuild";

    # "devenv:enterShell".after = [ "langnet:setup" "langnet:jsinstall" ];
  };

  # https://devenv.sh/tests/
  # enterTest = ''
  #   echo "Running tests"
  #   git --version | grep --color=auto "${pkgs.git.version}"
  # '';

  # scripts.run-test-suite.exec = ''
  #   $HOME/.local/bin/poe test
  # '';

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
