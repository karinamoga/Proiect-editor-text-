#ifndef TEXT_EDITOR_H
#define TEXT_EDITOR_H

// TextEditor structure - TODO: define your own fields here

typedef enum {
    ORIGINAL_BUFFER,
    ADD_BUFFER
} BufferType;

//  piece reprezentand un segment de text prin lista dublu inl.
typedef struct Piece {
    BufferType buffer;
    int start;   // pozitia de start in buffer
    int len;
    struct Piece *next; // urm piesa in lista
    struct Piece *prev; // piesa de dinainte in lista 
} Piece;


typedef struct TTextEditor {

  char *original_buffer;
  int original_size;
    
  char *add_buffer;
  int add_buffer_size; // sizeul curent
  int add_buffer_capacity;
    
  Piece *head; // primu piece in lista
  Piece *tail; // ult piece in lista
    
  int global_cursor; // poz cursorului < total_len
  int total_len; // lungimea totala a textului
} TextEditor;

// ============================================================================
// API Functions - You MUST implement all of these
// ============================================================================

// Create a new text editor
// filename: if not NULL, load content from this file
// text: if not NULL (and filename is NULL), initialize with this text
// global_cursor: initial cursor position
TextEditor *create_table(const char *filename, const char *text, int global_cursor);

// Move cursor by 'advance' positions (can be negative for backwards)
void advance_cursor(TextEditor *editor, int advance);

// Get current cursor position
int show_global_cursor(TextEditor *editor);

// Get total text length
int show_total_len(TextEditor *editor);

// Insert text at current cursor position
void add_text(TextEditor *editor, char *text);

// Delete 'length' characters before cursor
void delete_text(TextEditor *editor, int length);

// Extract full text as allocated string (caller must free)
char *extract_current_text(TextEditor *editor);

// Save text to file or return via text pointer
void save_current_text(TextEditor *editor, const char *filename, char **text, int *global_cursor);

// ============================================================================
// Helper functions (optional - you can define your own)
// ============================================================================

#endif // TEXT_EDITOR_H
