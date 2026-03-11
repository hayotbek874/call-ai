{ pkgs, ... }: {
  channel = "stable-23.11"; # or "unstable"
  
  packages = [
    pkgs.nodejs_20
    pkgs.python312
    pkgs.python312Packages.pip
  ];

  env = {};

  idx = {
    extensions = [
      "dsznajder.es7-react-js-snippets"
    ];

    previews = {
      enable = true;
      previews = {
        web = {
          command = ["npm" "run" "dev" "--" "--port" "$PORT" "--host" "0.0.0.0"];
          manager = "web";
        };
      };
    };

    workspace = {
      onCreate = {
        npm-install = "npm install";
      };
      onStart = {};
    };
  };
}