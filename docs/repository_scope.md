# Repository scope and provenance

Prepared from the working Pi without moving, renaming, overwriting or deleting operational source files. Changes exist in a separate review checkout. The base is existing `main` commit `d886c56fc5e42f9a3d6233802b194ccd44191e87`; history is retained.

The preferred launcher, V3 bridge and both mission planners are copied byte-for-byte from current Pi files. Existing relay, diagnostics and source configuration remain. Two old wrappers have their relay path corrected in review copies only.

Existing OpenVINS source is retained because it was already committed project research content; removing this substantial prior source is outside the cleanup scope. Its package manifests, examples, simulations, calibration examples and original licenses remain together. It is not required by the preferred RTAB-Map pipeline. No additional external ROS package is vendored. No project-level license was found or added.

Removed from the proposed checkout only: tracked named launcher backups/recovery snapshots, superseded BA5 experimental launchers, and generated TF graph files. They remain in Git history; original Pi files are untouched. Untracked bridge V2/older bridge, the feature-700 experiment, dated script archive, bags, logs, reports, caches, ROS build/install/log trees, nested Git metadata, environment secrets and binaries are excluded. Historical parameter dump `config/odom_before_ba_test.yaml` remains explicitly labeled as a reference, not runtime defaults.

No CAD/ANSYS files or project-specific simulation files were found in scope. No private IP, SSH destination or credentials are added to documentation. Existing GitHub history is not rewritten; scans of the proposed tree cannot remove anything previously published in history.
