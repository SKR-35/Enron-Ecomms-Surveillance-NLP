# deploy_shinyapps.R
#
# Deploy Enron E-Comms Surveillance NLP Dashboard to shinyapps.io.
#
# Run from the repository root:
#   source("deploy_shinyapps.R")
#
# Before first deployment, uncomment and fill setAccountInfo() once.
# Get token info from shinyapps.io > Account > Tokens.

library(rsconnect)

# rsconnect::setAccountInfo(
#   name   = "",
#   token  = "",
#   secret = ""
# )

# -------------------------------------------------------------------
# Files required by the dashboard
# -------------------------------------------------------------------

app_files <- c(
  "app.R",
  "README.md",
  "LICENSE",
  "reports/methodology.md",

  # Dashboard data layer
  list.files("data/dashboard", full.names = TRUE, recursive = TRUE),

  # Small output summaries used by the app
  list.files("data/outputs", pattern = "\\.csv$", full.names = TRUE),

  # Optional notebooks / docs, if you want them bundled
  list.files("notebooks", pattern = "\\.ipynb$", full.names = TRUE)
)

# Keep only files that exist. This makes the deploy script robust
# if README, LICENSE or notebooks are added later.
app_files <- app_files[file.exists(app_files)]

# -------------------------------------------------------------------
# Deploy
# -------------------------------------------------------------------

rsconnect::deployApp(
  appDir = ".",
  appFiles = app_files,
  appName = "enron-ecomms-surveillance-nlp",
  appTitle = "Enron E-Comms Surveillance NLP Dashboard",
  forceUpdate = TRUE
)
