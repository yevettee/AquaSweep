// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice
#include "aqua_interfaces/msg/detail/tank_status__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `fish_type`
#include "rosidl_runtime_c/string_functions.h"

bool
aqua_interfaces__msg__TankStatus__init(aqua_interfaces__msg__TankStatus * msg)
{
  if (!msg) {
    return false;
  }
  // pollution_level
  // fish_type
  if (!rosidl_runtime_c__String__init(&msg->fish_type)) {
    aqua_interfaces__msg__TankStatus__fini(msg);
    return false;
  }
  // fish_count
  // fish_count_suspicious
  return true;
}

void
aqua_interfaces__msg__TankStatus__fini(aqua_interfaces__msg__TankStatus * msg)
{
  if (!msg) {
    return;
  }
  // pollution_level
  // fish_type
  rosidl_runtime_c__String__fini(&msg->fish_type);
  // fish_count
  // fish_count_suspicious
}

bool
aqua_interfaces__msg__TankStatus__are_equal(const aqua_interfaces__msg__TankStatus * lhs, const aqua_interfaces__msg__TankStatus * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // pollution_level
  if (lhs->pollution_level != rhs->pollution_level) {
    return false;
  }
  // fish_type
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->fish_type), &(rhs->fish_type)))
  {
    return false;
  }
  // fish_count
  if (lhs->fish_count != rhs->fish_count) {
    return false;
  }
  // fish_count_suspicious
  if (lhs->fish_count_suspicious != rhs->fish_count_suspicious) {
    return false;
  }
  return true;
}

bool
aqua_interfaces__msg__TankStatus__copy(
  const aqua_interfaces__msg__TankStatus * input,
  aqua_interfaces__msg__TankStatus * output)
{
  if (!input || !output) {
    return false;
  }
  // pollution_level
  output->pollution_level = input->pollution_level;
  // fish_type
  if (!rosidl_runtime_c__String__copy(
      &(input->fish_type), &(output->fish_type)))
  {
    return false;
  }
  // fish_count
  output->fish_count = input->fish_count;
  // fish_count_suspicious
  output->fish_count_suspicious = input->fish_count_suspicious;
  return true;
}

aqua_interfaces__msg__TankStatus *
aqua_interfaces__msg__TankStatus__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__TankStatus * msg = (aqua_interfaces__msg__TankStatus *)allocator.allocate(sizeof(aqua_interfaces__msg__TankStatus), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(aqua_interfaces__msg__TankStatus));
  bool success = aqua_interfaces__msg__TankStatus__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
aqua_interfaces__msg__TankStatus__destroy(aqua_interfaces__msg__TankStatus * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    aqua_interfaces__msg__TankStatus__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
aqua_interfaces__msg__TankStatus__Sequence__init(aqua_interfaces__msg__TankStatus__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__TankStatus * data = NULL;

  if (size) {
    data = (aqua_interfaces__msg__TankStatus *)allocator.zero_allocate(size, sizeof(aqua_interfaces__msg__TankStatus), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = aqua_interfaces__msg__TankStatus__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        aqua_interfaces__msg__TankStatus__fini(&data[i - 1]);
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
aqua_interfaces__msg__TankStatus__Sequence__fini(aqua_interfaces__msg__TankStatus__Sequence * array)
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
      aqua_interfaces__msg__TankStatus__fini(&array->data[i]);
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

aqua_interfaces__msg__TankStatus__Sequence *
aqua_interfaces__msg__TankStatus__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__TankStatus__Sequence * array = (aqua_interfaces__msg__TankStatus__Sequence *)allocator.allocate(sizeof(aqua_interfaces__msg__TankStatus__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = aqua_interfaces__msg__TankStatus__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
aqua_interfaces__msg__TankStatus__Sequence__destroy(aqua_interfaces__msg__TankStatus__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    aqua_interfaces__msg__TankStatus__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
aqua_interfaces__msg__TankStatus__Sequence__are_equal(const aqua_interfaces__msg__TankStatus__Sequence * lhs, const aqua_interfaces__msg__TankStatus__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!aqua_interfaces__msg__TankStatus__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
aqua_interfaces__msg__TankStatus__Sequence__copy(
  const aqua_interfaces__msg__TankStatus__Sequence * input,
  aqua_interfaces__msg__TankStatus__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(aqua_interfaces__msg__TankStatus);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    aqua_interfaces__msg__TankStatus * data =
      (aqua_interfaces__msg__TankStatus *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!aqua_interfaces__msg__TankStatus__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          aqua_interfaces__msg__TankStatus__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!aqua_interfaces__msg__TankStatus__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
