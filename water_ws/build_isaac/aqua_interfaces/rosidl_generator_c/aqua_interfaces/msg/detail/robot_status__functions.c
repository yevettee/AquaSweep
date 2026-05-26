// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from aqua_interfaces:msg/RobotStatus.idl
// generated code does not contain a copyright notice
#include "aqua_interfaces/msg/detail/robot_status__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
aqua_interfaces__msg__RobotStatus__init(aqua_interfaces__msg__RobotStatus * msg)
{
  if (!msg) {
    return false;
  }
  // state
  // battery_level
  // collision_force
  return true;
}

void
aqua_interfaces__msg__RobotStatus__fini(aqua_interfaces__msg__RobotStatus * msg)
{
  if (!msg) {
    return;
  }
  // state
  // battery_level
  // collision_force
}

bool
aqua_interfaces__msg__RobotStatus__are_equal(const aqua_interfaces__msg__RobotStatus * lhs, const aqua_interfaces__msg__RobotStatus * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // state
  if (lhs->state != rhs->state) {
    return false;
  }
  // battery_level
  if (lhs->battery_level != rhs->battery_level) {
    return false;
  }
  // collision_force
  if (lhs->collision_force != rhs->collision_force) {
    return false;
  }
  return true;
}

bool
aqua_interfaces__msg__RobotStatus__copy(
  const aqua_interfaces__msg__RobotStatus * input,
  aqua_interfaces__msg__RobotStatus * output)
{
  if (!input || !output) {
    return false;
  }
  // state
  output->state = input->state;
  // battery_level
  output->battery_level = input->battery_level;
  // collision_force
  output->collision_force = input->collision_force;
  return true;
}

aqua_interfaces__msg__RobotStatus *
aqua_interfaces__msg__RobotStatus__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__RobotStatus * msg = (aqua_interfaces__msg__RobotStatus *)allocator.allocate(sizeof(aqua_interfaces__msg__RobotStatus), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(aqua_interfaces__msg__RobotStatus));
  bool success = aqua_interfaces__msg__RobotStatus__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
aqua_interfaces__msg__RobotStatus__destroy(aqua_interfaces__msg__RobotStatus * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    aqua_interfaces__msg__RobotStatus__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
aqua_interfaces__msg__RobotStatus__Sequence__init(aqua_interfaces__msg__RobotStatus__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__RobotStatus * data = NULL;

  if (size) {
    data = (aqua_interfaces__msg__RobotStatus *)allocator.zero_allocate(size, sizeof(aqua_interfaces__msg__RobotStatus), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = aqua_interfaces__msg__RobotStatus__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        aqua_interfaces__msg__RobotStatus__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
aqua_interfaces__msg__RobotStatus__Sequence__fini(aqua_interfaces__msg__RobotStatus__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      aqua_interfaces__msg__RobotStatus__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

aqua_interfaces__msg__RobotStatus__Sequence *
aqua_interfaces__msg__RobotStatus__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__RobotStatus__Sequence * array = (aqua_interfaces__msg__RobotStatus__Sequence *)allocator.allocate(sizeof(aqua_interfaces__msg__RobotStatus__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = aqua_interfaces__msg__RobotStatus__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
aqua_interfaces__msg__RobotStatus__Sequence__destroy(aqua_interfaces__msg__RobotStatus__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    aqua_interfaces__msg__RobotStatus__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
aqua_interfaces__msg__RobotStatus__Sequence__are_equal(const aqua_interfaces__msg__RobotStatus__Sequence * lhs, const aqua_interfaces__msg__RobotStatus__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!aqua_interfaces__msg__RobotStatus__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
aqua_interfaces__msg__RobotStatus__Sequence__copy(
  const aqua_interfaces__msg__RobotStatus__Sequence * input,
  aqua_interfaces__msg__RobotStatus__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(aqua_interfaces__msg__RobotStatus);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    aqua_interfaces__msg__RobotStatus * data =
      (aqua_interfaces__msg__RobotStatus *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!aqua_interfaces__msg__RobotStatus__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          aqua_interfaces__msg__RobotStatus__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!aqua_interfaces__msg__RobotStatus__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
