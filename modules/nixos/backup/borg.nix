{ ... }:

{
  services.borgbackup.jobs.dummy-local = {
    paths = [
      "/home/alex/borg-test/source"
    ];
    repo = "/home/alex/borg-test/repo";

    doInit = true;
    encryption.mode = "none";

    compression = "auto,zstd";

    # no timer for learning
    startAt = [ ];
  };  
}
