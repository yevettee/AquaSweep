// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__STRUCT_H_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'fish_type'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/TankStatus in the package aqua_interfaces.
typedef struct aqua_interfaces__msg__TankStatus
{
  float pollution_level;
  rosidl_runtime_c__String fish_type;
  int32_t fish_count;
  int32_t fish_count_suspicious;
} aqua_interfaces__msg__TankStatus;

// Struct for a sequence of aqua_interfaces__msg__TankStatus.
typedef struct aqua_interfaces__msg__TankStatus__Sequence
{
  aqua_interfaces__msg__TankStatus * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__msg__TankStatus__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__STRUCT_H_
