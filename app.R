# ============================================================
# app.R
# Enron E-Comms Surveillance NLP Dashboard
# ============================================================

library(shiny)
library(shinydashboard)
library(plotly)
library(DT)
library(dplyr)
library(scales)
library(htmltools)
library(stringr)

# Optional but recommended for parquet files
if (!requireNamespace("arrow", quietly = TRUE)) {
  stop("Package 'arrow' is required. Install with: install.packages('arrow')")
}

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

DATA_DASHBOARD <- "data/dashboard"
DATA_OUTPUTS <- "data/outputs"

emails_dashboard_path <- file.path(DATA_DASHBOARD, "emails_dashboard.parquet")
nodes_dashboard_path  <- file.path(DATA_DASHBOARD, "network_nodes_dashboard.parquet")
edges_dashboard_path  <- file.path(DATA_DASHBOARD, "network_edges_dashboard.parquet")
kpi_path              <- file.path(DATA_DASHBOARD, "kpi_summary.csv")
risk_band_path        <- file.path(DATA_DASHBOARD, "risk_band_summary.csv")
monthly_path          <- file.path(DATA_DASHBOARD, "monthly_email_volume.csv")
risk_category_path    <- file.path(DATA_OUTPUTS, "risk_phrase_category_summary.csv")
top_risky_path        <- file.path(DATA_OUTPUTS, "top_risk_scored_emails.csv")

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

emails <- arrow::read_parquet(emails_dashboard_path)
nodes  <- arrow::read_parquet(nodes_dashboard_path)
edges  <- arrow::read_parquet(edges_dashboard_path)
kpis   <- read.csv(kpi_path, stringsAsFactors = FALSE)
risk_band_summary <- read.csv(risk_band_path, stringsAsFactors = FALSE)
monthly_email_volume <- read.csv(monthly_path, stringsAsFactors = FALSE)

risk_category_summary <- if (file.exists(risk_category_path)) {
  read.csv(risk_category_path, stringsAsFactors = FALSE)
} else {
  data.frame(risk_category = character(), email_count = numeric(), email_pct = numeric())
}

top_risky_emails <- if (file.exists(top_risky_path)) {
  read.csv(top_risky_path, stringsAsFactors = FALSE)
} else {
  emails |> arrange(desc(final_risk_score)) |> head(250)
}

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || all(is.na(x))) y else x
}

format_num <- function(x) scales::comma(as.numeric(x), accuracy = 1)

get_kpi <- function(metric_name, default = 0) {
  val <- kpis$value[kpis$metric == metric_name]
  if (!length(val)) return(default)
  val[[1]]
}

value_box <- function(value, subtitle, icon_name, color = "blue") {
  shinydashboard::valueBox(
    value = value,
    subtitle = subtitle,
    icon = icon(icon_name),
    color = color,
    width = 3
  )
}

make_dt <- function(df, page_length = 10, order_col = NULL, order_dir = "desc") {
  dt_options <- list(
    pageLength = page_length,
    scrollX = TRUE,
    autoWidth = TRUE,
    dom = "Blfrtip",
    buttons = list(
      list(
        extend = "csv",
        text = "Export CSV",
        filename = "enron_ecomms_export",
        exportOptions = list(
          modifier = list(page = "all", search = "applied", order = "applied")
        )
      )
    )
  )

  if (!is.null(order_col)) {
    dt_options$order <- list(list(order_col, order_dir))
  }

  DT::datatable(
    df,
    rownames = FALSE,
    filter = "top",
    extensions = "Buttons",
    options = dt_options
  )
}

plotly_config <- function(p) {
  plotly::config(p, displaylogo = FALSE, responsive = TRUE)
}

safe_top <- function(df, n = 15) {
  if (nrow(df) == 0) return(df)
  head(df, n)
}

parse_enron_dates <- function(x) {
  clean <- as.character(x)
  clean <- gsub("\\s*\\([^)]*\\)", "", clean)
  clean <- gsub("\\s+", " ", trimws(clean))

  formats <- c(
    "%a, %d %b %Y %H:%M:%S %z",
    "%d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M %z",
    "%d %b %Y %H:%M %z",
    "%a, %d %b %Y %H:%M:%S",
    "%d %b %Y %H:%M:%S"
  )

  out <- rep(as.POSIXct(NA, tz = "UTC"), length(clean))

  for (fmt in formats) {
    missing <- is.na(out) & !is.na(clean) & nzchar(clean)
    if (!any(missing)) break

    parsed <- suppressWarnings(as.POSIXct(clean[missing], format = fmt, tz = "UTC"))
    out[missing] <- parsed
  }

  out
}

create_monthly_volume <- function(emails_df, start_year = 1998, end_year = 2002) {
  if ("date" %in% names(emails_df)) {
    parsed_dates <- parse_enron_dates(emails_df$date)
    tmp <- emails_df |>
      mutate(
        parsed_date = parsed_dates,
        month_date = as.Date(format(parsed_date, "%Y-%m-01")),
        month = format(month_date, "%Y-%m")
      )
  } else if ("email_month_period" %in% names(emails_df)) {
    tmp <- emails_df |>
      mutate(
        month = as.character(email_month_period),
        month_date = as.Date(paste0(month, "-01"))
      )
  } else {
    return(data.frame(
      month = character(),
      email_count = numeric(),
      avg_risk_score = numeric(),
      high_risk_count = numeric(),
      medium_risk_count = numeric()
    ))
  }

  start_date <- as.Date(sprintf("%s-01-01", start_year))
  end_date <- as.Date(sprintf("%s-12-01", end_year))

  monthly <- tmp |>
    filter(!is.na(month_date), month_date >= start_date, month_date <= end_date) |>
    group_by(month_date, month) |>
    summarise(
      email_count = n(),
      avg_risk_score = mean(final_risk_score, na.rm = TRUE),
      high_risk_count = sum(risk_band == "High", na.rm = TRUE),
      medium_risk_count = sum(risk_band == "Medium", na.rm = TRUE),
      .groups = "drop"
    )

  all_months <- data.frame(
    month_date = seq.Date(start_date, end_date, by = "month")
  ) |>
    mutate(month = format(month_date, "%Y-%m"))

  all_months |>
    left_join(monthly, by = c("month_date", "month")) |>
    mutate(
      email_count = ifelse(is.na(email_count), 0, email_count),
      avg_risk_score = ifelse(is.na(avg_risk_score), 0, round(avg_risk_score, 2)),
      high_risk_count = ifelse(is.na(high_risk_count), 0, high_risk_count),
      medium_risk_count = ifelse(is.na(medium_risk_count), 0, medium_risk_count)
    ) |>
    arrange(month_date)
}

# Override stale monthly CSV with a robust month series derived from email dates.
monthly_email_volume <- create_monthly_volume(emails, start_year = 1998, end_year = 2002)

info_banner <- function() {
  div(
    class = "source-banner",
    strong("Enron E-Comms Surveillance NLP Dashboard"), br(),
    "Data source: Enron Email Dataset", br(),
    "Pipeline: emails → parsing → text features → risk phrases → network analytics → risk scoring → dashboard.", br(),
    "Purpose: compliance-style surveillance analytics and investigation prioritization."
  )
}

how_to_box <- function(title, ..., width = 12) {
  box(
    width = width,
    title = title,
    status = "primary",
    solidHeader = TRUE,
    class = "compact-explain",
    div(class = "explain-box", ...)
  )
}

# ------------------------------------------------------------
# Palettes
# ------------------------------------------------------------

dashboard_palettes <- list(
  "Tableau Original" = list(primary = "#4E79A7", secondary = "#59A14F", accent = "#F28E2B", bg = "#FFFFFF"),
  "Modern Bright" = list(primary = "#2E6FBB", secondary = "#43A047", accent = "#FB8C00", bg = "#F7F9FB"),
  "Muted Audit" = list(primary = "#466A92", secondary = "#4F8A5B", accent = "#D5A021", bg = "#FFFFFF"),
  "Default" = list(primary = "#337AB7", secondary = "#5DA5DA", accent = "#2C3E50", bg = "#F7F9FB"),
  "SAP Blue" = list(primary = "#0A6ED1", secondary = "#2E90FA", accent = "#0854A0", bg = "#F7FBFF"),
  "Finance Green" = list(primary = "#2E7D32", secondary = "#43A047", accent = "#1B5E20", bg = "#F6FBF8"),
  "Executive Dark" = list(primary = "#6366F1", secondary = "#2563EB", accent = "#06B6D4", bg = "#F8FAFC"),
  "Warm Amber" = list(primary = "#D97706", secondary = "#F59E0B", accent = "#7C2D12", bg = "#FFFAF0"),
  "Ocean Teal" = list(primary = "#006D77", secondary = "#83C5BE", accent = "#E9C46A", bg = "#F6FCFC"),
  "Slate Professional" = list(primary = "#475569", secondary = "#64748B", accent = "#0F766E", bg = "#F8FAFC"),
  "Audit Pastel" = list(primary = "#78A083", secondary = "#A8DADC", accent = "#457B9D", bg = "#FFFFFF"),
  "High Contrast" = list(primary = "#0072B2", secondary = "#009E73", accent = "#E69F00", bg = "#FFFFFF")
)

get_palette <- function(name) dashboard_palettes[[name]] %||% dashboard_palettes[["Muted Audit"]]

palette_css <- function(palette_name = "Muted Audit") {
  p <- get_palette(palette_name)

  tags$style(HTML(sprintf("
    .content-wrapper, .right-side { background-color: %s; overflow-x: hidden; }
    .main-header .logo, .main-header .navbar, .skin-blue .main-header .logo,
    .skin-blue .main-header .navbar, .skin-blue .main-header .logo:hover { background-color: %s !important; }

    .main-header .logo {
      font-weight: 800;
      white-space: nowrap !important;
      width: 620px !important;
      text-align: left !important;
      padding-left: 56px !important;
      font-size: 18px !important;
    }

    .main-header .navbar { margin-left: 620px !important; }

    .main-header .navbar .sidebar-toggle,
    .main-header .sidebar-toggle {
      position: fixed !important;
      left: 8px !important;
      top: 8px !important;
      width: 42px !important;
      height: 42px !important;
      z-index: 20000 !important;
      background: transparent !important;
      text-align: center !important;
    }

    .main-header .navbar .sidebar-toggle:hover,
    .main-header .sidebar-toggle:hover { background: rgba(0,0,0,0.12) !important; }

    .skin-blue .main-sidebar, .skin-blue .left-side, .main-sidebar {
      background-color: %s !important;
    }

    .skin-blue .sidebar-menu > li > a {
      color: #ffffff !important;
      border-left: 3px solid transparent;
    }

    .skin-blue .sidebar-menu > li:hover > a,
    .skin-blue .sidebar-menu > li.active > a {
      background-color: rgba(0,0,0,0.18) !important;
      color: #ffffff !important;
    }

    .sidebar-menu > li.active > a { border-left-color: %s !important; }

    .box {
      border-radius: 10px;
      border-top: 3px solid %s;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

    .box.box-primary { border-top-color: %s; }
    .box.box-solid.box-primary > .box-header {
      background-color: %s;
      border-color: %s;
    }

    .source-banner, .explain-box {
      background: #ffffff;
      border-left: 5px solid %s;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 15px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      font-size: 14px;
      line-height: 1.45;
      word-break: break-word;
      overflow-wrap: anywhere;
    }

    .source-banner strong, .explain-box strong { color: %s; }

    .compact-explain .box-body { padding: 10px 12px !important; }

    .sidebar-export-block {
      padding: 12px 15px;
      border-top: 1px solid rgba(255,255,255,0.12);
    }

    .sidebar-export-block .shiny-input-container,
    .sidebar-export-block .form-group,
    .sidebar-export-block .selectize-control,
    .sidebar-export-block .selectize-input,
    .sidebar-export-block .btn,
    .sidebar-export-block .btn-default {
      width: 100%% !important;
      max-width: 100%% !important;
      box-sizing: border-box;
    }

    .sidebar-export-block .btn,
    .sidebar-export-block .btn-default {
      margin-bottom: 10px;
      text-align: left;
      border-radius: 7px;
      font-weight: 700;
      color: #1f2933 !important;
      background: #ffffff !important;
      border: 1px solid rgba(255,255,255,0.55) !important;
      opacity: 1 !important;
    }

    .observations-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .observation-card {
      background: #ffffff;
      border-left: 5px solid %s;
      border-radius: 10px;
      padding: 14px 16px;
      box-shadow: 0 1px 5px rgba(0,0,0,0.08);
      min-height: 140px;
    }

    .observation-theme {
      color: %s;
      font-weight: 800;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 8px;
    }

    .observation-title {
      font-size: 15px;
      font-weight: 650;
      line-height: 1.35;
      margin-bottom: 10px;
    }

    .observation-why {
      font-size: 13px;
      color: #4b5563;
      line-height: 1.35;
    }

    .dataTables_wrapper { font-size: 13px; }

    @media (max-width: 1100px) {
      .observations-grid { grid-template-columns: 1fr; }
    }
  ",
  p$bg, p$primary, p$primary, p$accent, p$primary, p$primary, p$primary, p$primary,
  p$accent, p$primary, p$accent, p$primary)))
}

# ------------------------------------------------------------
# Plot functions
# ------------------------------------------------------------

plot_risk_band_distribution <- function(df, bar_color = "#466A92") {
  band_order <- c("High", "Medium", "Low")
  df <- df |>
    mutate(
      risk_band = factor(risk_band, levels = band_order),
      label = scales::comma(email_count)
    ) |>
    arrange(risk_band)

  plotly::plot_ly(
    df,
    x = ~risk_band,
    y = ~email_count,
    type = "bar",
    text = ~label,
    textposition = "outside",
    cliponaxis = FALSE,
    marker = list(color = bar_color),
    hovertemplate = "Risk band: %{x}<br>Emails: %{y:,}<extra></extra>"
  ) |>
    plotly::layout(
      title = "Risk Band Distribution",
      xaxis = list(title = "Risk band"),
      yaxis = list(title = "Emails", rangemode = "tozero"),
      margin = list(t = 70)
    ) |>
    plotly_config()
}

plot_monthly_volume <- function(df, line_color = "#466A92") {
  df <- df |>
    mutate(month_date = as.Date(paste0(month, "-01"))) |>
    arrange(month_date)

  plotly::plot_ly(
    df,
    x = ~month_date,
    y = ~email_count,
    type = "scatter",
    mode = "lines",
    line = list(color = line_color, width = 2),
    fill = "tozeroy",
    fillcolor = "rgba(70,106,146,0.12)",
    hovertemplate = "Month: %{x|%Y-%m}<br>Emails: %{y:,}<extra></extra>"
  ) |>
    plotly::add_markers(
      data = df |> filter(email_count > 0),
      x = ~month_date,
      y = ~email_count,
      marker = list(color = line_color, size = 5),
      hovertemplate = "Month: %{x|%Y-%m}<br>Emails: %{y:,}<extra></extra>"
    ) |>
    plotly::layout(
      title = "Monthly Email Volume, 1998-2002",
      xaxis = list(title = "Month", tickformat = "%Y-%m"),
      yaxis = list(title = "Emails"),
      showlegend = FALSE
    ) |>
    plotly_config()
}

plot_risk_categories <- function(df, bar_color = "#466A92") {
  if (nrow(df) == 0) {
    return(plotly::plot_ly() |> plotly::layout(title = "No risk category data found"))
  }

  df <- df |> arrange(email_count)
  plotly::plot_ly(
    df,
    x = ~email_count,
    y = ~reorder(risk_category, email_count),
    type = "bar",
    orientation = "h",
    marker = list(color = bar_color),
    hovertemplate = "Category: %{y}<br>Emails: %{x:,}<extra></extra>"
  ) |>
    plotly::layout(
      title = "Risk Phrase Categories",
      xaxis = list(title = "Email count"),
      yaxis = list(title = ""),
      margin = list(l = 170)
    ) |>
    plotly_config()
}

plot_top_risky_senders <- function(emails, n = 15, min_emails = 50, bar_color = "#466A92") {
  df <- emails |>
    group_by(from_email) |>
    summarise(
      email_count = n(),
      avg_risk_score = mean(final_risk_score, na.rm = TRUE),
      medium_high_count = sum(risk_band %in% c("Medium", "High"), na.rm = TRUE),
      high_count = sum(risk_band == "High", na.rm = TRUE),
      .groups = "drop"
    ) |>
    filter(email_count >= min_emails) |>
    arrange(desc(medium_high_count), desc(avg_risk_score)) |>
    slice_head(n = n) |>
    mutate(label = str_trunc(from_email, 38)) |>
    arrange(medium_high_count)

  plotly::plot_ly(
    df,
    x = ~medium_high_count,
    y = ~reorder(label, medium_high_count),
    type = "bar",
    orientation = "h",
    marker = list(color = bar_color),
    text = ~paste0(
      "Sender: ", from_email,
      "<br>Email count: ", email_count,
      "<br>Medium/High count: ", medium_high_count,
      "<br>High count: ", high_count,
      "<br>Avg risk score: ", round(avg_risk_score, 2)
    ),
    hoverinfo = "text"
  ) |>
    plotly::layout(
      title = paste0("Top Risky Senders (min ", min_emails, " emails)"),
      xaxis = list(title = "Medium/High risk emails"),
      yaxis = list(title = ""),
      margin = list(l = 260)
    ) |>
    plotly_config()
}

plot_top_network_nodes <- function(nodes, metric = "weighted_total_email_count", n = 15, bar_color = "#466A92") {
  df <- nodes |>
    arrange(desc(.data[[metric]])) |>
    slice_head(n = n) |>
    mutate(label = str_trunc(node, 38)) |>
    arrange(.data[[metric]])

  plotly::plot_ly(
    df,
    x = ~.data[[metric]],
    y = ~reorder(label, .data[[metric]]),
    type = "bar",
    orientation = "h",
    marker = list(color = bar_color),
    text = ~paste0(
      "Node: ", node,
      "<br>Metric: ", round(.data[[metric]], 5),
      "<br>Total email volume: ", weighted_total_email_count,
      "<br>Total connections: ", total_connection_count,
      "<br>Risky emails: ", risky_email_total
    ),
    hoverinfo = "text"
  ) |>
    plotly::layout(
      title = paste0("Top Network Nodes by ", metric),
      xaxis = list(title = metric),
      yaxis = list(title = ""),
      margin = list(l = 260)
    ) |>
    plotly_config()
}

plot_top_edges <- function(edges, n = 15, min_count = 1, bar_color = "#466A92") {
  df <- edges |>
    filter(email_count >= min_count) |>
    arrange(desc(email_count), desc(risky_email_count)) |>
    slice_head(n = n) |>
    mutate(label = paste0(str_trunc(source, 23), " → ", str_trunc(target, 23))) |>
    arrange(email_count)

  plotly::plot_ly(
    df,
    x = ~email_count,
    y = ~reorder(label, email_count),
    type = "bar",
    orientation = "h",
    marker = list(color = bar_color),
    text = ~paste0(
      "Source: ", source,
      "<br>Target: ", target,
      "<br>Email count: ", email_count,
      "<br>Risky email count: ", risky_email_count,
      "<br>Risky email pct: ", risky_email_pct, "%"
    ),
    hoverinfo = "text"
  ) |>
    plotly::layout(
      title = paste0("Top Communication Edges (min ", min_count, " emails)"),
      xaxis = list(title = "Email count"),
      yaxis = list(title = ""),
      margin = list(l = 300)
    ) |>
    plotly_config()
}


plot_relationship_network <- function(edges, n = 35, min_count = 10, node_color = "#466A92", accent_color = "#D5A021") {
  df <- edges |>
    filter(email_count >= min_count) |>
    arrange(desc(email_count), desc(risky_email_count)) |>
    slice_head(n = n)

  if (nrow(df) == 0) {
    return(plotly::plot_ly() |> plotly::layout(title = "No network relationships for selected filters"))
  }

  node_names <- sort(unique(c(df$source, df$target)))
  theta <- seq(0, 2 * pi, length.out = length(node_names) + 1)[-1]

  node_df <- data.frame(
    node = node_names,
    x = cos(theta),
    y = sin(theta),
    stringsAsFactors = FALSE
  )

  edge_df <- df |>
    left_join(node_df, by = c("source" = "node")) |>
    rename(x0 = x, y0 = y) |>
    left_join(node_df, by = c("target" = "node")) |>
    rename(x1 = x, y1 = y)

  p <- plotly::plot_ly()

  for (i in seq_len(nrow(edge_df))) {
    p <- p |>
      plotly::add_segments(
        x = edge_df$x0[i], y = edge_df$y0[i],
        xend = edge_df$x1[i], yend = edge_df$y1[i],
        line = list(color = "rgba(70,106,146,0.28)", width = max(1, log1p(edge_df$email_count[i]) / 2)),
        hoverinfo = "text",
        text = paste0(
          edge_df$source[i], " → ", edge_df$target[i],
          "<br>Email count: ", edge_df$email_count[i],
          "<br>Risky email count: ", edge_df$risky_email_count[i]
        ),
        showlegend = FALSE
      )
  }

  p |>
    plotly::add_markers(
      data = node_df,
      x = ~x, y = ~y,
      marker = list(size = 12, color = node_color, line = list(color = accent_color, width = 1)),
      text = ~node,
      hovertemplate = "Node: %{text}<extra></extra>",
      showlegend = FALSE
    ) |>
    plotly::layout(
      title = paste0("Top Relationship Network Graph (top ", n, " edges)"),
      xaxis = list(visible = FALSE),
      yaxis = list(visible = FALSE),
      margin = list(l = 10, r = 10, t = 50, b = 10)
    ) |>
    plotly_config()
}

force_layout_ego <- function(node_names, edge_df, selected_node, iterations = 350, seed = 42) {
  set.seed(seed)

  n <- length(node_names)
  coords <- data.frame(
    node = node_names,
    x = runif(n, -1, 1),
    y = runif(n, -1, 1),
    stringsAsFactors = FALSE
  )

  # Keep selected entity near the center, but allow the graph to breathe.
  coords$x[coords$node == selected_node] <- 0
  coords$y[coords$node == selected_node] <- 0

  area <- 10
  k <- sqrt(area / max(n, 1))

  edge_index <- edge_df |>
    mutate(
      source_i = match(source, coords$node),
      target_i = match(target, coords$node),
      edge_weight_scaled = pmin(4, pmax(0.5, log1p(email_count) / 2))
    ) |>
    filter(!is.na(source_i), !is.na(target_i), source_i != target_i)

  for (iter in seq_len(iterations)) {
    disp_x <- rep(0, n)
    disp_y <- rep(0, n)

    # Repulsion
    for (i in seq_len(n)) {
      dx <- coords$x[i] - coords$x
      dy <- coords$y[i] - coords$y
      dist <- sqrt(dx^2 + dy^2) + 0.01

      force <- (k^2) / dist
      disp_x[i] <- disp_x[i] + sum((dx / dist) * force)
      disp_y[i] <- disp_y[i] + sum((dy / dist) * force)
    }

    # Attraction
    for (e in seq_len(nrow(edge_index))) {
      i <- edge_index$source_i[e]
      j <- edge_index$target_i[e]

      dx <- coords$x[i] - coords$x[j]
      dy <- coords$y[i] - coords$y[j]
      dist <- sqrt(dx^2 + dy^2) + 0.01

      force <- ((dist^2) / k) * edge_index$edge_weight_scaled[e] * 0.045

      disp_x[i] <- disp_x[i] - (dx / dist) * force
      disp_y[i] <- disp_y[i] - (dy / dist) * force
      disp_x[j] <- disp_x[j] + (dx / dist) * force
      disp_y[j] <- disp_y[j] + (dy / dist) * force
    }

    # Mild gravity toward center
    disp_x <- disp_x - coords$x * 0.015
    disp_y <- disp_y - coords$y * 0.015

    # Pin the selected node softly to center
    center_i <- which(coords$node == selected_node)
    if (length(center_i)) {
      disp_x[center_i] <- disp_x[center_i] - coords$x[center_i] * 0.8
      disp_y[center_i] <- disp_y[center_i] - coords$y[center_i] * 0.8
    }

    temp <- 0.12 * (1 - iter / iterations) + 0.01
    step <- sqrt(disp_x^2 + disp_y^2) + 0.01

    coords$x <- coords$x + (disp_x / step) * pmin(step, temp)
    coords$y <- coords$y + (disp_y / step) * pmin(step, temp)
  }

  coords
}

plot_ego_network <- function(selected_node, edges, n = 25, node_color = "#466A92", accent_color = "#D5A021") {
  first_degree <- edges |>
    filter(source == selected_node | target == selected_node) |>
    arrange(desc(email_count), desc(risky_email_count)) |>
    mutate(counterparty = ifelse(source == selected_node, target, source)) |>
    distinct(counterparty, .keep_all = TRUE) |>
    slice_head(n = n)

  if (nrow(first_degree) == 0) {
    return(plotly::plot_ly() |> plotly::layout(title = "No relationships found for selected entity"))
  }

  ego_nodes <- unique(c(selected_node, first_degree$counterparty))

  # Include selected-node links and counterparty-to-counterparty links.
  sub_edges <- edges |>
    filter(source %in% ego_nodes, target %in% ego_nodes, source != target) |>
    arrange(desc(email_count), desc(risky_email_count)) |>
    slice_head(n = 80)

  # Guarantee all first-degree selected-node links are present.
  selected_edges <- first_degree |> select(source, target, email_count, risky_email_count, risky_email_pct)
  sub_edges <- bind_rows(sub_edges, selected_edges) |>
    distinct(source, target, .keep_all = TRUE)

  node_names <- sort(unique(c(sub_edges$source, sub_edges$target, selected_node)))
  coords <- force_layout_ego(node_names, sub_edges, selected_node)

  node_stats <- sub_edges |>
    group_by(node = source) |>
    summarise(sent_weight = sum(email_count), .groups = "drop") |>
    full_join(
      sub_edges |>
        group_by(node = target) |>
        summarise(received_weight = sum(email_count), .groups = "drop"),
      by = "node"
    ) |>
    mutate(
      sent_weight = ifelse(is.na(sent_weight), 0, sent_weight),
      received_weight = ifelse(is.na(received_weight), 0, received_weight),
      total_weight = sent_weight + received_weight
    )

  node_df <- coords |>
    left_join(node_stats, by = "node") |>
    mutate(
      total_weight = ifelse(is.na(total_weight), 1, total_weight),
      node_size = ifelse(node == selected_node, 24, pmax(8, pmin(18, 6 + log1p(total_weight) * 1.8))),
      node_color = ifelse(node == selected_node, accent_color, node_color),
      node_label = ifelse(node == selected_node, "Selected entity", "Counterparty")
    )

  edge_df <- sub_edges |>
    left_join(coords, by = c("source" = "node")) |>
    rename(x0 = x, y0 = y) |>
    left_join(coords, by = c("target" = "node")) |>
    rename(x1 = x, y1 = y) |>
    mutate(
      edge_width = pmax(1, pmin(7, log1p(email_count) / 1.8)),
      edge_color = ifelse(source == selected_node | target == selected_node, "rgba(70,106,146,0.45)", "rgba(120,130,145,0.22)")
    )

  p <- plotly::plot_ly()

  for (i in seq_len(nrow(edge_df))) {
    p <- p |>
      plotly::add_segments(
        x = edge_df$x0[i], y = edge_df$y0[i],
        xend = edge_df$x1[i], yend = edge_df$y1[i],
        line = list(color = edge_df$edge_color[i], width = edge_df$edge_width[i]),
        hoverinfo = "text",
        text = paste0(
          edge_df$source[i], " → ", edge_df$target[i],
          "<br>Email count: ", edge_df$email_count[i],
          "<br>Risky email count: ", edge_df$risky_email_count[i],
          "<br>Risky pct: ", edge_df$risky_email_pct[i], "%"
        ),
        showlegend = FALSE
      )
  }

  p |>
    plotly::add_markers(
      data = node_df,
      x = ~x, y = ~y,
      marker = list(
        size = ~node_size,
        color = ~node_color,
        opacity = 0.92,
        line = list(color = "#1f2933", width = 0.8)
      ),
      text = ~paste0(
        node,
        "<br>", node_label,
        "<br>Total relationship volume: ", total_weight
      ),
      hoverinfo = "text",
      showlegend = FALSE
    ) |>
    plotly::layout(
      title = paste0("Selected Entity Ego Network: ", selected_node),
      xaxis = list(visible = FALSE, zeroline = FALSE),
      yaxis = list(visible = FALSE, zeroline = FALSE),
      margin = list(l = 10, r = 10, t = 60, b = 10)
    ) |>
    plotly_config()
}

# ------------------------------------------------------------
# Observations
# ------------------------------------------------------------

observations_df <- function() {
  tibble::tibble(
    theme = c(
      "Data product", "Parsing quality", "Risk phrase layer", "Risk scoring",
      "Network analytics", "Investigation workflow", "Timeline caveat", "Governance"
    ),
    observation = c(
      "The raw CSV was converted into a structured surveillance data mart with parsed email fields, text features, risk phrase flags, network metrics and dashboard-ready outputs.",
      "The parser successfully processed more than 517k emails with only 12 parse errors, which is negligible for this scale.",
      "Risk phrase detection flagged a meaningful review population while preserving a large low-risk majority.",
      "The final score creates a narrow high-risk population and a broader medium-risk population suitable for triage.",
      "The communication graph contains tens of thousands of nodes and hundreds of thousands of directed communication relationships.",
      "The dashboard supports a case-review style workflow: identify risky senders, inspect their network position, then review candidate emails.",
      "The public Enron dataset contains unusual date outliers. Timeline analysis should usually focus on the main Enron period rather than blindly interpreting every timestamp.",
      "All results are review signals. A high score does not imply misconduct and should be combined with professional judgment."
    ),
    why_it_matters = c(
      "It shows that the project is an end-to-end pipeline rather than a single notebook.",
      "It gives confidence that downstream NLP and network analytics are based on a complete dataset.",
      "It creates interpretable surveillance signals without requiring unavailable supervised labels.",
      "It mirrors real surveillance operations where only a small share of records should become high-priority alerts.",
      "It demonstrates graph analytics capability: hubs, brokers, repeated relationships and risk flow.",
      "It turns analytics into an investigation-oriented product, which is stronger than isolated charts.",
      "It prevents misleading management conclusions from known historical-data quality quirks.",
      "It keeps the dashboard analytically useful and legally cautious."
    )
  )
}

observation_cards <- function() {
  df <- observations_df()

  tagList(lapply(seq_len(nrow(df)), function(i) {
    div(
      class = "observation-card",
      div(class = "observation-theme", df$theme[i]),
      div(class = "observation-title", df$observation[i]),
      div(class = "observation-why", strong("Why it matters: "), df$why_it_matters[i])
    )
  }))
}

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

ui <- dashboardPage(
  skin = "blue",
  dashboardHeader(title = "Enron E-Comms Surveillance NLP Dashboard", titleWidth = 620),

  dashboardSidebar(
    sidebarMenu(
      id = "tabs",
      menuItem("Overview", tabName = "overview", icon = icon("chart-line")),
      menuItem("Risk Signals", tabName = "risk_signals", icon = icon("exclamation-triangle")),
      menuItem("Network Analytics", tabName = "network", icon = icon("project-diagram")),
      menuItem("Investigation View", tabName = "investigation", icon = icon("search")),
      menuItem("Observations", tabName = "observations", icon = icon("lightbulb")),
      menuItem("Data Tables", tabName = "tables", icon = icon("table"))
    ),
    div(
      class = "sidebar-export-block",
      selectInput(
        "palette_choice",
        "Color palette",
        choices = names(dashboard_palettes),
        selected = "Muted Audit"
      )
    )
  ),

  dashboardBody(
    uiOutput("palette_css"),

    tabItems(
      tabItem(
        tabName = "overview",
        info_banner(),

        fluidRow(
          value_box(format_num(get_kpi("total_emails")), "Emails", "envelope", "blue"),
          value_box(format_num(get_kpi("emails_with_any_risk_phrase")), "Emails with risk phrases", "flag", "purple"),
          value_box(format_num(get_kpi("unique_network_nodes")), "Network nodes", "users", "green"),
          value_box(format_num(get_kpi("unique_network_edges")), "Communication edges", "project-diagram", "yellow")
        ),

        fluidRow(
          box(width = 6, title = "Risk Band Distribution", status = "primary", solidHeader = TRUE, plotlyOutput("risk_band_plot", height = "360px")),
          box(width = 6, title = "Monthly Email Volume", status = "primary", solidHeader = TRUE, plotlyOutput("monthly_volume_plot", height = "360px"))
        ),

        fluidRow(
          how_to_box(
            "How to read this dashboard",
            p("This dashboard converts raw Enron emails into an investigation-oriented surveillance data product."),
            p("The workflow parses raw messages, creates text features, detects compliance-style risk phrases, builds communication networks and assigns review-prioritization scores."),
            p("A high score is a triage signal. It does not imply misconduct.")
          )
        ),

        fluidRow(
          box(width = 12, title = "Top Communication Relationships", status = "primary", solidHeader = TRUE, plotlyOutput("top_edges_overview", height = "480px"))
        )
      ),

      tabItem(
        tabName = "risk_signals",

        fluidRow(
          column(
            width = 3,
            box(
              width = 12, title = "Filters", status = "primary", solidHeader = TRUE,
              sliderInput("risk_sender_min_emails", "Minimum sender emails", min = 1, max = 500, value = 50, step = 10),
              selectInput("risk_band_filter", "Risk band", choices = c("All", sort(unique(emails$risk_band))), selected = "All")
            ),
            how_to_box(
              "How to read risk signals",
              p("Risk phrase categories identify compliance-style language such as confidentiality, legal/regulatory terms, urgency, deletion, concealment and offline-communication indicators."),
              p("These rules are interpretable screening signals. They are not a supervised classifier."),
              width = 12
            )
          ),
          column(
            width = 9,
            box(width = 12, title = "Risk Phrase Categories", status = "primary", solidHeader = TRUE, plotlyOutput("risk_category_plot", height = "420px")),
            box(width = 12, title = "Top Risky Senders", status = "primary", solidHeader = TRUE, plotlyOutput("top_risky_senders_plot", height = "460px"))
          )
        ),

        fluidRow(
          box(width = 12, title = "Top Risk-Scored Emails", status = "primary", solidHeader = TRUE, DTOutput("top_risky_emails_table"))
        )
      ),

      tabItem(
        tabName = "network",

        fluidRow(
          column(
            width = 3,
            box(
              width = 12, title = "Network controls", status = "primary", solidHeader = TRUE,
              selectInput(
                "network_metric",
                "Node metric",
                choices = c(
                  "Weighted total email count" = "weighted_total_email_count",
                  "Betweenness centrality" = "betweenness_centrality",
                  "Total connections" = "total_connection_count",
                  "Risky email total" = "risky_email_total"
                ),
                selected = "weighted_total_email_count"
              ),
              sliderInput("edge_min_count", "Minimum edge emails", min = 1, max = 200, value = 10, step = 5)
            ),
            how_to_box(
              "How to read network analytics",
              p("Nodes are email addresses. Directed edges are sender-recipient communication relationships."),
              p("Activity metrics identify communication hubs. Betweenness centrality highlights potential bridge or broker-like actors."),
              p("Risky email totals show where phrase-based risk concentrates in the communication graph."),
              width = 12
            )
          ),
          column(
            width = 9,
            box(width = 12, title = "Top Network Nodes", status = "primary", solidHeader = TRUE, plotlyOutput("top_network_nodes_plot", height = "460px")),
            box(width = 12, title = "Top Communication Edges", status = "primary", solidHeader = TRUE, plotlyOutput("top_edges_network_plot", height = "460px"))
          )
        ),

        fluidRow(
          box(width = 12, title = "Network Node Table", status = "primary", solidHeader = TRUE, DTOutput("network_nodes_table"))
        )
      ),

      tabItem(
        tabName = "investigation",

        fluidRow(
          column(
            width = 3,
            box(
              width = 12, title = "Investigation controls", status = "primary", solidHeader = TRUE,
              selectizeInput(
                "employee_select",
                "Employee / email address",
                choices = sort(unique(nodes$node)),
                selected = nodes |> arrange(desc(risky_email_total)) |> slice(1) |> pull(node),
                options = list(maxOptions = 1000, placeholder = "Search email address")
              )
            ),
            how_to_box(
              "How to read investigation view",
              p("Select one employee or email account to inspect its network position, top counterparties and highest-scored emails."),
              p("This mirrors a case-review workflow: entity selection → communication context → candidate messages."),
              width = 12
            )
          ),
          column(
            width = 9,
            fluidRow(
              valueBoxOutput("investigation_email_volume", width = 3),
              valueBoxOutput("investigation_connections", width = 3),
              valueBoxOutput("investigation_betweenness", width = 3),
              valueBoxOutput("investigation_risky_total", width = 3)
            ),
            box(width = 12, title = "Selected Entity Network", status = "primary", solidHeader = TRUE, plotlyOutput("investigation_ego_network_plot", height = "520px")),
            box(width = 6, title = "Top Outgoing Relationships", status = "primary", solidHeader = TRUE, DTOutput("investigation_outgoing_table")),
            box(width = 6, title = "Top Incoming Relationships", status = "primary", solidHeader = TRUE, DTOutput("investigation_incoming_table")),
            box(width = 12, title = "Highest-Risk Emails Sent by Selected Entity", status = "primary", solidHeader = TRUE, DTOutput("investigation_email_table"))
          )
        )
      ),

      tabItem(
        tabName = "observations",

        fluidRow(
          how_to_box(
            "Observations and Disclaimer",
            p("This page summarizes the analytical story from the dashboard."),
            p("The objective is to identify review candidates and communication patterns, not to determine wrongdoing."),
            p("Risk scores, phrase flags and network metrics are screening signals requiring further investigation and professional judgment.")
          )
        ),

        fluidRow(
          box(width = 12, title = "Key observations", status = "primary", solidHeader = TRUE, div(class = "observations-grid", observation_cards()))
        )
      ),

      tabItem(
        tabName = "tables",
        fluidRow(box(width = 12, title = "Email Dashboard Table", status = "primary", solidHeader = TRUE, DTOutput("emails_table"))),
        fluidRow(box(width = 12, title = "Network Edges", status = "primary", solidHeader = TRUE, DTOutput("edges_table"))),
        fluidRow(box(width = 12, title = "Network Nodes", status = "primary", solidHeader = TRUE, DTOutput("nodes_table"))),
        fluidRow(box(width = 12, title = "Risk Category Summary", status = "primary", solidHeader = TRUE, DTOutput("risk_category_table")))
      )
    )
  )
)

# ------------------------------------------------------------
# Server
# ------------------------------------------------------------

server <- function(input, output, session) {

  active_palette <- reactive(get_palette(input$palette_choice))
  output$palette_css <- renderUI(palette_css(input$palette_choice))

  filtered_emails_for_risk <- reactive({
    df <- emails
    if (!is.null(input$risk_band_filter) && input$risk_band_filter != "All") {
      df <- df |> filter(risk_band == input$risk_band_filter)
    }
    df
  })

  selected_node_metrics <- reactive({
    nodes |> filter(node == input$employee_select)
  })

  # Overview
  output$risk_band_plot <- renderPlotly({
    plot_risk_band_distribution(risk_band_summary, bar_color = active_palette()$primary)
  })

  output$monthly_volume_plot <- renderPlotly({
    plot_monthly_volume(monthly_email_volume, line_color = active_palette()$primary)
  })

  output$top_edges_overview <- renderPlotly({
    plot_top_edges(edges, n = 15, min_count = 10, bar_color = active_palette()$primary)
  })

  # Risk signals
  output$risk_category_plot <- renderPlotly({
    plot_risk_categories(risk_category_summary, bar_color = active_palette()$primary)
  })

  output$top_risky_senders_plot <- renderPlotly({
    plot_top_risky_senders(
      filtered_emails_for_risk(),
      n = 15,
      min_emails = input$risk_sender_min_emails,
      bar_color = active_palette()$primary
    )
  })

  output$top_risky_emails_table <- renderDT({
    top_risky_emails |>
      select(any_of(c(
        "date", "from_email", "to_email", "subject", "final_risk_score", "risk_band",
        "risk_phrase_score", "risk_phrase_category_count",
        "sender_network_volume", "sender_connection_count", "sender_betweenness"
      ))) |>
      arrange(desc(final_risk_score)) |>
      make_dt(page_length = 15, order_col = 4)
  }, server = FALSE)

  # Network

  output$top_network_nodes_plot <- renderPlotly({
    plot_top_network_nodes(
      nodes,
      metric = input$network_metric,
      n = 15,
      bar_color = active_palette()$primary
    )
  })

  output$top_edges_network_plot <- renderPlotly({
    plot_top_edges(
      edges,
      n = 15,
      min_count = input$edge_min_count,
      bar_color = active_palette()$primary
    )
  })

  output$network_nodes_table <- renderDT({
    nodes |>
      select(any_of(c(
        "node", "weighted_total_email_count", "weighted_in_email_count", "weighted_out_email_count",
        "total_connection_count", "degree_centrality", "betweenness_centrality",
        "risky_email_total", "risky_emails_sent", "risky_emails_received"
      ))) |>
      arrange(desc(.data[[input$network_metric]])) |>
      make_dt(page_length = 15)
  }, server = FALSE)

  # Investigation
  output$investigation_email_volume <- renderValueBox({
    m <- selected_node_metrics()
    value_box(format_num(m$weighted_total_email_count %||% 0), "Email volume", "envelope", "blue")
  })

  output$investigation_connections <- renderValueBox({
    m <- selected_node_metrics()
    value_box(format_num(m$total_connection_count %||% 0), "Connections", "project-diagram", "purple")
  })

  output$investigation_betweenness <- renderValueBox({
    m <- selected_node_metrics()
    val <- if (nrow(m)) round(m$betweenness_centrality, 4) else 0
    value_box(val, "Betweenness", "share-alt", "green")
  })

  output$investigation_risky_total <- renderValueBox({
    m <- selected_node_metrics()
    value_box(format_num(m$risky_email_total %||% 0), "Risky emails", "flag", "yellow")
  })

  output$investigation_ego_network_plot <- renderPlotly({
    plot_ego_network(
      input$employee_select,
      edges,
      n = 25,
      node_color = active_palette()$primary,
      accent_color = active_palette()$accent
    )
  })

  output$investigation_outgoing_table <- renderDT({
    edges |>
      filter(source == input$employee_select) |>
      arrange(desc(email_count), desc(risky_email_count)) |>
      select(source, target, email_count, risky_email_count, risky_email_pct, avg_risk_phrase_score, max_risk_phrase_score) |>
      head(50) |>
      make_dt(page_length = 10)
  }, server = FALSE)

  output$investigation_incoming_table <- renderDT({
    edges |>
      filter(target == input$employee_select) |>
      arrange(desc(email_count), desc(risky_email_count)) |>
      select(source, target, email_count, risky_email_count, risky_email_pct, avg_risk_phrase_score, max_risk_phrase_score) |>
      head(50) |>
      make_dt(page_length = 10)
  }, server = FALSE)

  output$investigation_email_table <- renderDT({
    emails |>
      filter(from_email == input$employee_select) |>
      arrange(desc(final_risk_score)) |>
      select(any_of(c(
        "date", "from_email", "to_email", "subject", "final_risk_score", "risk_band",
        "risk_phrase_score", "risk_phrase_category_count",
        "risk_confidentiality", "risk_concealment", "risk_deletion",
        "risk_urgency_pressure", "risk_legal_regulatory", "risk_financial_risk", "risk_offline_meeting"
      ))) |>
      head(100) |>
      make_dt(page_length = 10)
  }, server = FALSE)

  # Tables
  output$emails_table <- renderDT({
    emails |>
      select(any_of(c(
        "date", "from_email", "to_email", "subject", "body_length", "word_count",
        "final_risk_score", "risk_band", "risk_phrase_score", "risk_phrase_category_count"
      ))) |>
      arrange(desc(final_risk_score)) |>
      head(5000) |>
      make_dt(page_length = 15)
  }, server = FALSE)

  output$edges_table <- renderDT({
    edges |>
      arrange(desc(email_count), desc(risky_email_count)) |>
      head(5000) |>
      make_dt(page_length = 15)
  }, server = FALSE)

  output$nodes_table <- renderDT({
    nodes |>
      arrange(desc(weighted_total_email_count)) |>
      head(5000) |>
      make_dt(page_length = 15)
  }, server = FALSE)

  output$risk_category_table <- renderDT({
    risk_category_summary |> make_dt(page_length = 10)
  }, server = FALSE)
}

shinyApp(ui, server)
