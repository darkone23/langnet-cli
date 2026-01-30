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
 
    # some libraries for cltk deps (numpy, scipy)
    pkgs.zlib
    pkgs.gcc
    # pkgs.libgcc
    pkgs.gnumake
    pkgs.duckdb
    pkgs.sqlite

    pkgs.just
    pkgs.hl-log-viewer

    uvicorn-run
  ];

  # https://devenv.sh/languages/
  # languages.rust.enable = true;
  languages.python.enable = true;
  languages.python.package = pkgs.python311; # the version that currently works with CLTK
  languages.python.venv.enable = true;
  languages.python.venv.requirements = ./devenv.requirements.txt;
  
  # languages.python.poetry.package = (pkgs.poetry.override { python3 = pkgs.python311; });
  # languages.python.poetry.enable = true;
  # languages.python.poetry.activate.enable = true;
  # languages.python.poetry.install.enable = false;

  # languages.python.poetry.enable = true;
  # languages.python.poetry.package = (pkgs.poetry.override { python3 = pkgs.python311; });
  # languages.python.poetry.activate.enable = true;

  # languages.javascript.enable = true;
  # languages.javascript.npm.enable = true;
  # languages.javascript.bun.enable = true;
  # languages.typescript.enable = true;

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
    export TMP="${config.devenv.root}/tmp";
    export TMPDIR="${config.devenv.root}/tmp";
    export PYTHONPATH=$DEVENV_ROOT/src:$DEVENV_ROOT/.justscripts:$PYTHONPATH
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
