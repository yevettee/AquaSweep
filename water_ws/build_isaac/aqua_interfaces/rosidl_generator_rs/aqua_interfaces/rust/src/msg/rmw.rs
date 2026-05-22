#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__msg__RobotStatus() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__msg__RobotStatus__init(msg: *mut RobotStatus) -> bool;
    fn aqua_interfaces__msg__RobotStatus__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<RobotStatus>, size: usize) -> bool;
    fn aqua_interfaces__msg__RobotStatus__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<RobotStatus>);
    fn aqua_interfaces__msg__RobotStatus__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<RobotStatus>, out_seq: *mut rosidl_runtime_rs::Sequence<RobotStatus>) -> bool;
}

// Corresponds to aqua_interfaces__msg__RobotStatus
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct RobotStatus {

    // This member is not documented.
    #[allow(missing_docs)]
    pub state: u8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub battery_level: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub collision_force: f32,

}

impl RobotStatus {

    // This constant is not documented.
    #[allow(missing_docs)]
    pub const IDLE: u8 = 0;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const RUNNING: u8 = 1;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const PAUSED: u8 = 2;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const DISCHARGED: u8 = 3;

}


impl Default for RobotStatus {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__msg__RobotStatus__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__msg__RobotStatus__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for RobotStatus {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__RobotStatus__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__RobotStatus__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__RobotStatus__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for RobotStatus {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for RobotStatus where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/msg/RobotStatus";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__msg__RobotStatus() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__msg__PoolStatus() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__msg__PoolStatus__init(msg: *mut PoolStatus) -> bool;
    fn aqua_interfaces__msg__PoolStatus__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<PoolStatus>, size: usize) -> bool;
    fn aqua_interfaces__msg__PoolStatus__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<PoolStatus>);
    fn aqua_interfaces__msg__PoolStatus__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<PoolStatus>, out_seq: *mut rosidl_runtime_rs::Sequence<PoolStatus>) -> bool;
}

// Corresponds to aqua_interfaces__msg__PoolStatus
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct PoolStatus {

    // This member is not documented.
    #[allow(missing_docs)]
    pub pollution_level: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_type: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_count: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_count_suspicious: i32,

}



impl Default for PoolStatus {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__msg__PoolStatus__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__msg__PoolStatus__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for PoolStatus {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__PoolStatus__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__PoolStatus__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__PoolStatus__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for PoolStatus {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for PoolStatus where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/msg/PoolStatus";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__msg__PoolStatus() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__msg__PoolPhysicalVariables() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__msg__PoolPhysicalVariables__init(msg: *mut PoolPhysicalVariables) -> bool;
    fn aqua_interfaces__msg__PoolPhysicalVariables__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<PoolPhysicalVariables>, size: usize) -> bool;
    fn aqua_interfaces__msg__PoolPhysicalVariables__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<PoolPhysicalVariables>);
    fn aqua_interfaces__msg__PoolPhysicalVariables__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<PoolPhysicalVariables>, out_seq: *mut rosidl_runtime_rs::Sequence<PoolPhysicalVariables>) -> bool;
}

// Corresponds to aqua_interfaces__msg__PoolPhysicalVariables
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct PoolPhysicalVariables {

    // This member is not documented.
    #[allow(missing_docs)]
    pub buoyancy: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub drag: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub lift: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub viscosity: f32,

}



impl Default for PoolPhysicalVariables {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__msg__PoolPhysicalVariables__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__msg__PoolPhysicalVariables__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for PoolPhysicalVariables {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__PoolPhysicalVariables__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__PoolPhysicalVariables__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__msg__PoolPhysicalVariables__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for PoolPhysicalVariables {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for PoolPhysicalVariables where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/msg/PoolPhysicalVariables";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__msg__PoolPhysicalVariables() }
  }
}


