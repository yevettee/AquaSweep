# Individual fish status message
# Published to /pool_N/fish_M/status

# Fish identification
string fish_id              # Unique fish ID (e.g., "fish_0", "Sturgeon_1")
int32 pool_id               # Pool this fish belongs to

# Species classification (from YOLO detector)
string species              # "sturgeon", "salmon", etc.
float32 species_confidence  # Detection confidence (0.0-1.0)

# Status classification (from DINOv2 analyzer)
string status               # "alive" or "suspicious"
float32 status_confidence   # Classification confidence (0.0-1.0)

# Motion data
float32 velocity            # Relative velocity (normalized by frame diagonal)
float32 velocity_variance   # Velocity variance over time (irregular = suspicious)

# Position in image
float32 x_position          # X position in image (pixels)
float32 y_position          # Y position in image (pixels)
float32 bbox_width          # Bounding box width
float32 bbox_height         # Bounding box height

# Detection metadata
string detection_method     # "opencv", "sam2", or "yolo"
builtin_interfaces/Time timestamp
