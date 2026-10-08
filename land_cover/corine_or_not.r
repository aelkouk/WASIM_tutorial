# purpose: find out whether r500.use_ohne_glc is corine or not
# date: 2026-05-18

library(terra)
library(mapview)
library(data.table)

no_glc <- rast("sample-grids/r500.use_ohne_glc")
crs(no_glc) <- "EPSG:21781"

levels(no_glc) <-
  # fmt: skip
  rowwiseDT(
    id=, category=,
    1 ,  "1 - Wasserflaechen",
    2 ,  "2 - Bebauung",
    3 ,  "3 - Teilbebauung",
    4 ,  "4 - Wald",
    5 ,  "5 - offener_Wald",
    6 ,  "6 - Gebueschwald",
    7 ,  "7 - Ackerland",
    8 ,  "8 - Gruenland",
    9 ,  "9 - Obstbauflaechen",
    10,  "10 - Gebuesch",
    11,  "11 - verbuschtes_Weidel",
    12,  "12 - uebrige_Gruenfl",
    13,  "13 - Moore_Suempfe",
    14,  "14 - versteinte_wiesen",
    15,  "15 - Felsflaechen_Oedland"
    # 16,  "16 - Gletscher",
    # 21,  "21 - Deponien"
  )


corine_3035 <-
  file.path(
    "sample-grids",
    "u2018_clc2018_v2020_20u1_raster100m",
    "DATA",
    "U2018_CLC2018_V2020_20u1.tif"
  ) |>
  rast()

no_glc_ext_3035 <- ext(no_glc) |> project("EPSG:21781", "EPSG:3035")

corine_21781 <-
  corine_3035 |>
  crop(no_glc_ext_3035) |>
  project(no_glc) |>
  resample(no_glc, method = "modal")

mapview(corine_21781)
mapview(no_glc)

cats(corine_21781)
