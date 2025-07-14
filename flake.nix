{
  description = "SeqSee development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
    ...
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      inherit (nixpkgs) lib;

      # Load a uv workspace from a workspace root.
      workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};

      # Create package overlay from workspace.
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      # Extend generated overlay with build fixups
      pyprojectOverrides = _final: _prev: {
        # Implement build fixups here if needed.
      };

      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python311;

      # Construct package set
      pythonSet =
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyprojectOverrides
          ]
        );
    in {
      packages.default = pythonSet.mkVirtualEnv "seqsee-env" workspace.deps.default;

      apps.default = {
        type = "app";
        program = "${self.packages.${system}.default}/bin/seqsee";
      };

      devShells = {
        # Impure development shell using uv
        default = pkgs.mkShell {
          packages = [
            python
            pkgs.uv
            pkgs.basedpyright
            pkgs.ruff
            pkgs.git
          ];
          env =
            {
              UV_PYTHON_DOWNLOADS = "never";
              UV_PYTHON = python.interpreter;
            }
            // lib.optionalAttrs pkgs.stdenv.isLinux {
              LD_LIBRARY_PATH = lib.makeLibraryPath pkgs.pythonManylinuxPackages.manylinux1;
            };
          shellHook = ''
            unset PYTHONPATH
            echo "🚀 SeqSee development environment"
            echo "Python: $(python --version)"
            echo "uv: $(uv --version)"
            echo ""
            echo "Quick start:"
            echo "  uv sync                    # Install dependencies"
            echo "  uv run seqsee              # Run seqsee"
            echo "  uv build                   # Build package"
            echo ""
          '';
        };

        # Pure development shell using uv2nix
        pure = let
          # Create an overlay enabling editable mode for local dependencies.
          editableOverlay = workspace.mkEditablePyprojectOverlay {
            root = "$REPO_ROOT";
          };

          # Override previous set with our editable overlay.
          editablePythonSet = pythonSet.overrideScope (
            lib.composeManyExtensions [
              editableOverlay
              (final: prev: {
                seqsee = prev.seqsee.overrideAttrs (old: {
                  src = lib.fileset.toSource {
                    root = old.src;
                    fileset = lib.fileset.unions [
                      (old.src + "/pyproject.toml")
                      (old.src + "/README.md")
                      (old.src + "/seqsee")
                    ];
                  };
                  nativeBuildInputs =
                    old.nativeBuildInputs
                    ++ final.resolveBuildSystem {
                      editables = [];
                    };
                });
              })
            ]
          );

          # Build virtual environment, with local packages being editable.
          virtualenv = editablePythonSet.mkVirtualEnv "seqsee-dev-env" workspace.deps.all;
        in
          pkgs.mkShell {
            packages = [
              virtualenv
              pkgs.uv
              pkgs.basedpyright
              pkgs.ruff
              pkgs.git
            ];

            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = "${virtualenv}/bin/python";
              UV_PYTHON_DOWNLOADS = "never";
            };

            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              echo "🚀 SeqSee pure development environment (uv2nix)"
              echo "Python: $(python --version)"
              echo "uv: $(uv --version)"
              echo ""
              echo "Quick start:"
              echo "  seqsee                     # Run seqsee (editable)"
              echo "  uv build                   # Build package"
              echo ""
            '';
          };
      };
    });
}
