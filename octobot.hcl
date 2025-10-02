job "octobot" {
  type = "service"

  group "octobot" {
    count = 1

    restart {
      attempts = 0
      mode = "fail"
    }

    task "octobot" {
      driver = "docker"

      config {
        image = "drakkarsoftware/octobot:stable"
        
        ports = ["http"]

        # you should use a CSI or NFS instead of a volume
        volumes = [
          "./logs:/octobot/logs",
          "./backtesting:/octobot/backtesting",
          "./tentacles:/octobot/tentacles",
          "./user:/octobot/user"
        ]
      }

      env {
        PORT = 5001
      }

      resources {
        cpu    = 500  # MHz
        memory = 512  # MB
      }
    }

    network {
      port "http" {
        static = 80
        to     = 5001
      }
    }
  }
}
