# Task Organizer

A modern, feature-rich task management application built with Python and PyQt6. Task Organizer helps you efficiently manage your tasks with a clean, intuitive interface and powerful organizational features.

## Features

### Core Task Management
- **Hierarchical Task Organization**: Create tasks with subtasks and organize them in a tree structure
- **Multiple Categories**: Organize tasks by custom categories
- **Priority Levels**: Set and visualize task priorities with drag-and-drop reordering
- **Status Tracking**: Track task progress with customizable status types
- **Due Dates**: Set and monitor task deadlines

### User Interface
- **Task Pills**: Modern, color-coded task visualization with pill-style design
- **Dual View Modes**: Switch between compact and expanded views
- **Customizable Panels**: Configure left and right information panels (Category, Status, Links, Due Dates)
- **Tabbed Interface**: Organize different task views in tabs
- **Drag & Drop**: Intuitive task reordering and hierarchy management

### Customization
- **Font Settings**: Customize fonts for titles, descriptions, due dates, and panel text
- **Color Themes**: Personalize background colors for different task elements
- **OS-Specific Styling**: Native look and feel on macOS, Windows, and Linux
- **Panel Configuration**: Choose what information displays in task pill corners

### Data Management
- **SQLite Database**: Reliable local data storage
- **CSV Import/Export**: Easy data migration and backup
- **Memory Database**: Fast in-memory operations with automatic persistence
- **Data Integrity**: Automatic schema updates and data validation

### Advanced Features
- **Keyboard Shortcuts**: Comprehensive keyboard navigation and shortcuts
- **Task Attributes Management**: Create and manage custom categories, priorities, and statuses
- **Link Attachments**: Add external links to tasks
- **File Attachments**: Associate files with tasks
- **Search and Filter**: Quickly find tasks (planned feature)
- **Debug Logging**: Comprehensive logging for troubleshooting

## Screenshots

*Screenshots will be added here*

## Installation

### Prerequisites
- Python 3.9 or higher
- PyQt6

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/task-organizer.git
   cd task-organizer
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python src/main.py
   ```

## Usage

### Getting Started
1. **First Launch**: On first startup, the application will prompt you to choose a database location
2. **Create Tasks**: Use the "Add Task" button or Ctrl+N to create your first task
3. **Organize**: Drag and drop tasks to create hierarchies and reorder items
4. **Customize**: Access Settings to personalize fonts, colors, and display options

### Task Management
- **Add Task**: Click "Add Task" or use Ctrl+N
- **Edit Task**: Double-click a task or right-click and select "Edit"
- **Create Subtasks**: Drag a task onto another to create a parent-child relationship
- **Set Properties**: Use the task dialog to set category, priority, status, and due date

### Customization
- **Display Settings**: Settings → Display Settings to customize fonts and colors
- **Task Attributes**: Settings → Task Attributes to manage categories, priorities, and statuses
- **Panel Layout**: Configure what information appears in task pill corners

## Development

### Project Structure
```
task-organizer/
├── src/
│   ├── main.py                 # Application entry point
│   ├── database/               # Database management
│   ├── ui/                     # User interface components
│   ├── utils/                  # Utility functions and debugging
│   └── resources/              # Icons and assets
├── requirements.txt            # Python dependencies
└── README.md                  # This file
```

### Key Components
- **MainWindow**: Primary application window and coordination
- **TaskTreeWidget**: Hierarchical task display and management
- **TaskPillDelegate**: Custom rendering for task visualization
- **SettingsManager**: Configuration and preferences management
- **DatabaseManager**: SQLite database operations

### Debug Mode
Enable debug logging by running:
```bash
python src/main.py --debug
```

## Building

The application can be built into standalone executables:

### Windows
```bash
# Run the Windows build script
build.windows.bat
```

### macOS/Linux
```bash
# Run the Unix build script
./build_unix.sh
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the user interface
- Icons and graphics created using modern design principles
- Inspired by modern task management applications

## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/yourusername/task-organizer/issues) page
2. Create a new issue with detailed information about the problem
3. Include debug logs when reporting bugs (run with `--debug` flag)

## Roadmap

- [ ] Search and filtering capabilities
- [ ] Task templates
- [ ] Export to various formats (PDF, etc.)
- [ ] Plugin system
- [ ] Cloud synchronization
- [ ] Mobile companion app
- [ ] Team collaboration features

---

*Task Organizer - Organize your tasks, organize your life.*