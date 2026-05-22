
#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_Goal() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_Goal__init(msg: *mut CleanFloor_Goal) -> bool;
    fn aqua_interfaces__action__CleanFloor_Goal__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Goal>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_Goal__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Goal>);
    fn aqua_interfaces__action__CleanFloor_Goal__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_Goal>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Goal>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_Goal
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_Goal {

    // This member is not documented.
    #[allow(missing_docs)]
    pub structure_needs_at_least_one_member: u8,

}



impl Default for CleanFloor_Goal {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_Goal__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_Goal__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_Goal {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Goal__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Goal__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Goal__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_Goal {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_Goal where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_Goal";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_Goal() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_Result() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_Result__init(msg: *mut CleanFloor_Result) -> bool;
    fn aqua_interfaces__action__CleanFloor_Result__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Result>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_Result__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Result>);
    fn aqua_interfaces__action__CleanFloor_Result__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_Result>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Result>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_Result
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_Result {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,

}



impl Default for CleanFloor_Result {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_Result__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_Result__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_Result {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Result__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Result__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Result__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_Result {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_Result where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_Result";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_Result() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_Feedback() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_Feedback__init(msg: *mut CleanFloor_Feedback) -> bool;
    fn aqua_interfaces__action__CleanFloor_Feedback__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Feedback>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_Feedback__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Feedback>);
    fn aqua_interfaces__action__CleanFloor_Feedback__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_Feedback>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_Feedback>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_Feedback
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_Feedback {

    // This member is not documented.
    #[allow(missing_docs)]
    pub progress: f32,

}



impl Default for CleanFloor_Feedback {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_Feedback__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_Feedback__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_Feedback {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Feedback__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Feedback__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_Feedback__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_Feedback {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_Feedback where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_Feedback";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_Feedback() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_FeedbackMessage() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_FeedbackMessage__init(msg: *mut CleanFloor_FeedbackMessage) -> bool;
    fn aqua_interfaces__action__CleanFloor_FeedbackMessage__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_FeedbackMessage>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_FeedbackMessage__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_FeedbackMessage>);
    fn aqua_interfaces__action__CleanFloor_FeedbackMessage__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_FeedbackMessage>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_FeedbackMessage>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_FeedbackMessage
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_FeedbackMessage {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub feedback: super::super::action::rmw::CleanFloor_Feedback,

}



impl Default for CleanFloor_FeedbackMessage {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_FeedbackMessage__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_FeedbackMessage__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_FeedbackMessage {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_FeedbackMessage__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_FeedbackMessage__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_FeedbackMessage__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_FeedbackMessage {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_FeedbackMessage where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_FeedbackMessage";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_FeedbackMessage() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_Goal() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_Goal__init(msg: *mut CleanWall_Goal) -> bool;
    fn aqua_interfaces__action__CleanWall_Goal__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Goal>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_Goal__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Goal>);
    fn aqua_interfaces__action__CleanWall_Goal__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_Goal>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Goal>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_Goal
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_Goal {

    // This member is not documented.
    #[allow(missing_docs)]
    pub structure_needs_at_least_one_member: u8,

}



impl Default for CleanWall_Goal {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_Goal__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_Goal__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_Goal {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Goal__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Goal__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Goal__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_Goal {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_Goal where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_Goal";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_Goal() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_Result() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_Result__init(msg: *mut CleanWall_Result) -> bool;
    fn aqua_interfaces__action__CleanWall_Result__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Result>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_Result__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Result>);
    fn aqua_interfaces__action__CleanWall_Result__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_Result>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Result>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_Result
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_Result {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,

}



impl Default for CleanWall_Result {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_Result__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_Result__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_Result {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Result__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Result__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Result__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_Result {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_Result where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_Result";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_Result() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_Feedback() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_Feedback__init(msg: *mut CleanWall_Feedback) -> bool;
    fn aqua_interfaces__action__CleanWall_Feedback__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Feedback>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_Feedback__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Feedback>);
    fn aqua_interfaces__action__CleanWall_Feedback__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_Feedback>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_Feedback>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_Feedback
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_Feedback {

    // This member is not documented.
    #[allow(missing_docs)]
    pub progress: f32,

}



impl Default for CleanWall_Feedback {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_Feedback__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_Feedback__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_Feedback {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Feedback__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Feedback__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_Feedback__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_Feedback {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_Feedback where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_Feedback";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_Feedback() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_FeedbackMessage() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_FeedbackMessage__init(msg: *mut CleanWall_FeedbackMessage) -> bool;
    fn aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_FeedbackMessage>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_FeedbackMessage>);
    fn aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_FeedbackMessage>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_FeedbackMessage>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_FeedbackMessage
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_FeedbackMessage {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub feedback: super::super::action::rmw::CleanWall_Feedback,

}



impl Default for CleanWall_FeedbackMessage {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_FeedbackMessage__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_FeedbackMessage__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_FeedbackMessage {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_FeedbackMessage {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_FeedbackMessage where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_FeedbackMessage";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_FeedbackMessage() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_Goal() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_Goal__init(msg: *mut MoveFish_Goal) -> bool;
    fn aqua_interfaces__action__MoveFish_Goal__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Goal>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_Goal__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Goal>);
    fn aqua_interfaces__action__MoveFish_Goal__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_Goal>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Goal>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_Goal
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_Goal {
    /// "pool_1"
    pub source_pool: rosidl_runtime_rs::String,

    /// "pool_2"
    pub target_pool: rosidl_runtime_rs::String,

    /// 옮길 물고기 수 (-1 = all)
    pub fish_count: i32,

}



impl Default for MoveFish_Goal {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_Goal__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_Goal__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_Goal {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Goal__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Goal__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Goal__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_Goal {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_Goal where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_Goal";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_Goal() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_Result() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_Result__init(msg: *mut MoveFish_Result) -> bool;
    fn aqua_interfaces__action__MoveFish_Result__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Result>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_Result__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Result>);
    fn aqua_interfaces__action__MoveFish_Result__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_Result>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Result>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_Result
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_Result {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_moved: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,

}



impl Default for MoveFish_Result {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_Result__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_Result__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_Result {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Result__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Result__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Result__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_Result {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_Result where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_Result";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_Result() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_Feedback() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_Feedback__init(msg: *mut MoveFish_Feedback) -> bool;
    fn aqua_interfaces__action__MoveFish_Feedback__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Feedback>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_Feedback__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Feedback>);
    fn aqua_interfaces__action__MoveFish_Feedback__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_Feedback>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_Feedback>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_Feedback
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_Feedback {
    /// 0=moving_to_source, 1=picking, 2=moving_to_target, 3=placing
    pub phase: u8,

    /// 0.0 ~ 1.0
    pub progress: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_picked_so_far: i32,

}



impl Default for MoveFish_Feedback {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_Feedback__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_Feedback__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_Feedback {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Feedback__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Feedback__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_Feedback__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_Feedback {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_Feedback where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_Feedback";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_Feedback() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_FeedbackMessage() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_FeedbackMessage__init(msg: *mut MoveFish_FeedbackMessage) -> bool;
    fn aqua_interfaces__action__MoveFish_FeedbackMessage__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_FeedbackMessage>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_FeedbackMessage__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_FeedbackMessage>);
    fn aqua_interfaces__action__MoveFish_FeedbackMessage__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_FeedbackMessage>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_FeedbackMessage>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_FeedbackMessage
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_FeedbackMessage {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub feedback: super::super::action::rmw::MoveFish_Feedback,

}



impl Default for MoveFish_FeedbackMessage {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_FeedbackMessage__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_FeedbackMessage__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_FeedbackMessage {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_FeedbackMessage__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_FeedbackMessage__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_FeedbackMessage__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_FeedbackMessage {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_FeedbackMessage where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_FeedbackMessage";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_FeedbackMessage() }
  }
}




#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_SendGoal_Request() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_SendGoal_Request__init(msg: *mut CleanFloor_SendGoal_Request) -> bool;
    fn aqua_interfaces__action__CleanFloor_SendGoal_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Request>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_SendGoal_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Request>);
    fn aqua_interfaces__action__CleanFloor_SendGoal_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Request>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_SendGoal_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_SendGoal_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: super::super::action::rmw::CleanFloor_Goal,

}



impl Default for CleanFloor_SendGoal_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_SendGoal_Request__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_SendGoal_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_SendGoal_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_SendGoal_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_SendGoal_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_SendGoal_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_SendGoal_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_SendGoal_Request where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_SendGoal_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_SendGoal_Request() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_SendGoal_Response() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_SendGoal_Response__init(msg: *mut CleanFloor_SendGoal_Response) -> bool;
    fn aqua_interfaces__action__CleanFloor_SendGoal_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Response>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_SendGoal_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Response>);
    fn aqua_interfaces__action__CleanFloor_SendGoal_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_SendGoal_Response>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_SendGoal_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_SendGoal_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for CleanFloor_SendGoal_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_SendGoal_Response__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_SendGoal_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_SendGoal_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_SendGoal_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_SendGoal_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_SendGoal_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_SendGoal_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_SendGoal_Response where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_SendGoal_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_SendGoal_Response() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_GetResult_Request() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_GetResult_Request__init(msg: *mut CleanFloor_GetResult_Request) -> bool;
    fn aqua_interfaces__action__CleanFloor_GetResult_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Request>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_GetResult_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Request>);
    fn aqua_interfaces__action__CleanFloor_GetResult_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Request>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_GetResult_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_GetResult_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,

}



impl Default for CleanFloor_GetResult_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_GetResult_Request__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_GetResult_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_GetResult_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_GetResult_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_GetResult_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_GetResult_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_GetResult_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_GetResult_Request where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_GetResult_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_GetResult_Request() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_GetResult_Response() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanFloor_GetResult_Response__init(msg: *mut CleanFloor_GetResult_Response) -> bool;
    fn aqua_interfaces__action__CleanFloor_GetResult_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Response>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanFloor_GetResult_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Response>);
    fn aqua_interfaces__action__CleanFloor_GetResult_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanFloor_GetResult_Response>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanFloor_GetResult_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanFloor_GetResult_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub status: i8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub result: super::super::action::rmw::CleanFloor_Result,

}



impl Default for CleanFloor_GetResult_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanFloor_GetResult_Response__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanFloor_GetResult_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanFloor_GetResult_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_GetResult_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_GetResult_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanFloor_GetResult_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanFloor_GetResult_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanFloor_GetResult_Response where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanFloor_GetResult_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanFloor_GetResult_Response() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_SendGoal_Request() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_SendGoal_Request__init(msg: *mut CleanWall_SendGoal_Request) -> bool;
    fn aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Request>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Request>);
    fn aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Request>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_SendGoal_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_SendGoal_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: super::super::action::rmw::CleanWall_Goal,

}



impl Default for CleanWall_SendGoal_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_SendGoal_Request__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_SendGoal_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_SendGoal_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_SendGoal_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_SendGoal_Request where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_SendGoal_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_SendGoal_Request() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_SendGoal_Response() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_SendGoal_Response__init(msg: *mut CleanWall_SendGoal_Response) -> bool;
    fn aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Response>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Response>);
    fn aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_SendGoal_Response>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_SendGoal_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_SendGoal_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for CleanWall_SendGoal_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_SendGoal_Response__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_SendGoal_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_SendGoal_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_SendGoal_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_SendGoal_Response where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_SendGoal_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_SendGoal_Response() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_GetResult_Request() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_GetResult_Request__init(msg: *mut CleanWall_GetResult_Request) -> bool;
    fn aqua_interfaces__action__CleanWall_GetResult_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_GetResult_Request>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_GetResult_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_GetResult_Request>);
    fn aqua_interfaces__action__CleanWall_GetResult_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_GetResult_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_GetResult_Request>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_GetResult_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_GetResult_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,

}



impl Default for CleanWall_GetResult_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_GetResult_Request__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_GetResult_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_GetResult_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_GetResult_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_GetResult_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_GetResult_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_GetResult_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_GetResult_Request where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_GetResult_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_GetResult_Request() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_GetResult_Response() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__CleanWall_GetResult_Response__init(msg: *mut CleanWall_GetResult_Response) -> bool;
    fn aqua_interfaces__action__CleanWall_GetResult_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_GetResult_Response>, size: usize) -> bool;
    fn aqua_interfaces__action__CleanWall_GetResult_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<CleanWall_GetResult_Response>);
    fn aqua_interfaces__action__CleanWall_GetResult_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<CleanWall_GetResult_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<CleanWall_GetResult_Response>) -> bool;
}

// Corresponds to aqua_interfaces__action__CleanWall_GetResult_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CleanWall_GetResult_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub status: i8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub result: super::super::action::rmw::CleanWall_Result,

}



impl Default for CleanWall_GetResult_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__CleanWall_GetResult_Response__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__CleanWall_GetResult_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for CleanWall_GetResult_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_GetResult_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_GetResult_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__CleanWall_GetResult_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for CleanWall_GetResult_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for CleanWall_GetResult_Response where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/CleanWall_GetResult_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__CleanWall_GetResult_Response() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_SendGoal_Request() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_SendGoal_Request__init(msg: *mut MoveFish_SendGoal_Request) -> bool;
    fn aqua_interfaces__action__MoveFish_SendGoal_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Request>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_SendGoal_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Request>);
    fn aqua_interfaces__action__MoveFish_SendGoal_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Request>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_SendGoal_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_SendGoal_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: super::super::action::rmw::MoveFish_Goal,

}



impl Default for MoveFish_SendGoal_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_SendGoal_Request__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_SendGoal_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_SendGoal_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_SendGoal_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_SendGoal_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_SendGoal_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_SendGoal_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_SendGoal_Request where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_SendGoal_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_SendGoal_Request() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_SendGoal_Response() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_SendGoal_Response__init(msg: *mut MoveFish_SendGoal_Response) -> bool;
    fn aqua_interfaces__action__MoveFish_SendGoal_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Response>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_SendGoal_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Response>);
    fn aqua_interfaces__action__MoveFish_SendGoal_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_SendGoal_Response>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_SendGoal_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_SendGoal_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for MoveFish_SendGoal_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_SendGoal_Response__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_SendGoal_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_SendGoal_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_SendGoal_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_SendGoal_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_SendGoal_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_SendGoal_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_SendGoal_Response where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_SendGoal_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_SendGoal_Response() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_GetResult_Request() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_GetResult_Request__init(msg: *mut MoveFish_GetResult_Request) -> bool;
    fn aqua_interfaces__action__MoveFish_GetResult_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_GetResult_Request>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_GetResult_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_GetResult_Request>);
    fn aqua_interfaces__action__MoveFish_GetResult_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_GetResult_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_GetResult_Request>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_GetResult_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_GetResult_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub goal_id: unique_identifier_msgs::msg::rmw::UUID,

}



impl Default for MoveFish_GetResult_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_GetResult_Request__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_GetResult_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_GetResult_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_GetResult_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_GetResult_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_GetResult_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_GetResult_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_GetResult_Request where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_GetResult_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_GetResult_Request() }
  }
}


#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_GetResult_Response() -> *const std::ffi::c_void;
}

#[link(name = "aqua_interfaces__rosidl_generator_c")]
extern "C" {
    fn aqua_interfaces__action__MoveFish_GetResult_Response__init(msg: *mut MoveFish_GetResult_Response) -> bool;
    fn aqua_interfaces__action__MoveFish_GetResult_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_GetResult_Response>, size: usize) -> bool;
    fn aqua_interfaces__action__MoveFish_GetResult_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MoveFish_GetResult_Response>);
    fn aqua_interfaces__action__MoveFish_GetResult_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MoveFish_GetResult_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<MoveFish_GetResult_Response>) -> bool;
}

// Corresponds to aqua_interfaces__action__MoveFish_GetResult_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MoveFish_GetResult_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub status: i8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub result: super::super::action::rmw::MoveFish_Result,

}



impl Default for MoveFish_GetResult_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !aqua_interfaces__action__MoveFish_GetResult_Response__init(&mut msg as *mut _) {
        panic!("Call to aqua_interfaces__action__MoveFish_GetResult_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MoveFish_GetResult_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_GetResult_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_GetResult_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { aqua_interfaces__action__MoveFish_GetResult_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MoveFish_GetResult_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MoveFish_GetResult_Response where Self: Sized {
  const TYPE_NAME: &'static str = "aqua_interfaces/action/MoveFish_GetResult_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__aqua_interfaces__action__MoveFish_GetResult_Response() }
  }
}






#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanFloor_SendGoal() -> *const std::ffi::c_void;
}

// Corresponds to aqua_interfaces__action__CleanFloor_SendGoal
#[allow(missing_docs, non_camel_case_types)]
pub struct CleanFloor_SendGoal;

impl rosidl_runtime_rs::Service for CleanFloor_SendGoal {
    type Request = CleanFloor_SendGoal_Request;
    type Response = CleanFloor_SendGoal_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanFloor_SendGoal() }
    }
}




#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanFloor_GetResult() -> *const std::ffi::c_void;
}

// Corresponds to aqua_interfaces__action__CleanFloor_GetResult
#[allow(missing_docs, non_camel_case_types)]
pub struct CleanFloor_GetResult;

impl rosidl_runtime_rs::Service for CleanFloor_GetResult {
    type Request = CleanFloor_GetResult_Request;
    type Response = CleanFloor_GetResult_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanFloor_GetResult() }
    }
}




#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanWall_SendGoal() -> *const std::ffi::c_void;
}

// Corresponds to aqua_interfaces__action__CleanWall_SendGoal
#[allow(missing_docs, non_camel_case_types)]
pub struct CleanWall_SendGoal;

impl rosidl_runtime_rs::Service for CleanWall_SendGoal {
    type Request = CleanWall_SendGoal_Request;
    type Response = CleanWall_SendGoal_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanWall_SendGoal() }
    }
}




#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanWall_GetResult() -> *const std::ffi::c_void;
}

// Corresponds to aqua_interfaces__action__CleanWall_GetResult
#[allow(missing_docs, non_camel_case_types)]
pub struct CleanWall_GetResult;

impl rosidl_runtime_rs::Service for CleanWall_GetResult {
    type Request = CleanWall_GetResult_Request;
    type Response = CleanWall_GetResult_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__CleanWall_GetResult() }
    }
}




#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__MoveFish_SendGoal() -> *const std::ffi::c_void;
}

// Corresponds to aqua_interfaces__action__MoveFish_SendGoal
#[allow(missing_docs, non_camel_case_types)]
pub struct MoveFish_SendGoal;

impl rosidl_runtime_rs::Service for MoveFish_SendGoal {
    type Request = MoveFish_SendGoal_Request;
    type Response = MoveFish_SendGoal_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__MoveFish_SendGoal() }
    }
}




#[link(name = "aqua_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__MoveFish_GetResult() -> *const std::ffi::c_void;
}

// Corresponds to aqua_interfaces__action__MoveFish_GetResult
#[allow(missing_docs, non_camel_case_types)]
pub struct MoveFish_GetResult;

impl rosidl_runtime_rs::Service for MoveFish_GetResult {
    type Request = MoveFish_GetResult_Request;
    type Response = MoveFish_GetResult_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__aqua_interfaces__action__MoveFish_GetResult() }
    }
}


