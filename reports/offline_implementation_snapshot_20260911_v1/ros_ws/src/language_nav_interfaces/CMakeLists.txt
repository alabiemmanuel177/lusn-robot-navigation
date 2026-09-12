cmake_minimum_required(VERSION 3.8)
project(language_nav_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/LanguageInstruction.msg"
  "msg/LanguageHypotheses.msg"
  "msg/SemanticObservation.msg"
  "msg/BeliefGraph.msg"
  "msg/LanguageNavDecision.msg"
  "msg/Contradiction.msg"
  "msg/LanguageNavOutcome.msg"
  "msg/RouteRequest.msg"
  "msg/RouteEligibility.msg"
  "msg/RouteExecutionResult.msg"
  "msg/FailureMonitorState.msg"
  "msg/SemanticRouteProposal.msg"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
