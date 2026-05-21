// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__STRUCT_H_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/TankPhysicalVariables in the package aqua_interfaces.
typedef struct aqua_interfaces__msg__TankPhysicalVariables
{
  float buoyancy;
  float drag;
  float lift;
  float viscosity;
} aqua_interfaces__msg__TankPhysicalVariables;

// Struct for a sequence of aqua_interfaces__msg__TankPhysicalVariables.
typedef struct aqua_interfaces__msg__TankPhysicalVariables__Sequence
{
  aqua_interfaces__msg__TankPhysicalVariables * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__msg__TankPhysicalVariables__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__STRUCT_H_
