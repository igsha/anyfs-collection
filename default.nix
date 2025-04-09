{ lib, python3Packages }:

let
  toml = builtins.fromTOML (builtins.readFile ./pyproject.toml);

in python3Packages.buildPythonApplication {
  pname = toml.project.name;
  version = toml.project.version;
  pyproject = true;

  src = ./.;

  build-system = builtins.map (x: python3Packages.${x}) toml.build-system.requires;
  dependencies = builtins.map (x: python3Packages.${x}) toml.project.dependencies;

  postInstall = ''
    for f in $out/bin/*.py; do
      ln -s $out/bin/anyfs-wrapper.sh $out/bin/anyfs-$(basename $f)
    done
  '';

  meta = {
    description = toml.project.description;
    homepage = toml.project.urls.Homepage;
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ igsha ];
    platforms = lib.platforms.linux;
  };
}
