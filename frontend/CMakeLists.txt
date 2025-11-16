# Minimum required version of CMake
cmake_minimum_required(VERSION 3.10)

# Define the project name
project(DTTS_Project)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# Set the executable name to DTTS
set(EXECUTABLE_NAME DTTS)

# --- Configuration ---
# Set the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)


# --- Add External Subdirectories (Only GLFW) ---
add_subdirectory(glfw)

# --- Define ImGui Sources and Library ---

# Core ImGui Sources
file(GLOB IMGUI_CORE_SOURCES "./imgui/*.cpp")

# Backend (Platform/Renderer) Sources
set(IMGUI_BACKEND_SOURCES
    imgui/backends/imgui_impl_glfw.cpp
    imgui/backends/imgui_impl_opengl3.cpp
)

# Create a static library target for ImGui
add_library(imgui_library STATIC
    ${IMGUI_CORE_SOURCES}
    ${IMGUI_BACKEND_SOURCES}
)

# Set necessary include directories for the ImGui library
target_include_directories(imgui_library PUBLIC
    # Main ImGui header directory
    ${PROJECT_SOURCE_DIR}/imgui
    # ImGui Backend headers
    ${PROJECT_SOURCE_DIR}/imgui/backends
)

# Link imgui_library to glfw to inherit its include paths (fixes header not found error)
target_link_libraries(imgui_library PUBLIC glfw)


# --- Create the Executable ---
add_executable(${EXECUTABLE_NAME} main.cpp)
# examples
add_executable(examples examples.cpp)

# --- Link Executable to Libraries (CRITICAL FIX FOR UNDEFINED REFERENCE) ---

target_link_libraries(${EXECUTABLE_NAME}
    # These are PRIVATE dependencies for the DTTS executable.
    PRIVATE
        # **This line is essential:** Links the ImGui functions to the main program
        imgui_library
        # Link to OpenGL
        OpenGL
)

target_link_libraries(examples
    # These are PRIVATE dependencies for the DTTS executable.
    PRIVATE
        # **This line is essential:** Links the ImGui functions to the main program
        imgui_library
        # Link to OpenGL
        OpenGL
)
# --- (Optional) Platform-Specific Linking ---
if(UNIX)
    target_link_libraries(${EXECUTABLE_NAME} PRIVATE X11 pthread)
    target_link_libraries(examples PRIVATE X11 pthread)
elseif(APPLE)
    target_link_libraries(${EXECUTABLE_NAME} PRIVATE 
        "-framework Cocoa" 
        "-framework IOKit" 
        "-framework CoreVideo"
    )
    target_link_libraries(examples PRIVATE 
        "-framework Cocoa" 
        "-framework IOKit" 
        "-framework CoreVideo"
    )
endif()

# Set output directory for the executable
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)
