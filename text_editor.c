#include "text_editor.h"
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>


// functie helper de creare de piece
  Piece* create_piece(BufferType buffer, int start, int len){
    Piece *p = (Piece *)malloc(sizeof (Piece));
    if(!p)
    return NULL;

    // initializare de campuri
    p->buffer = buffer;
    p->start = start;
    p->len = len;
    p->next = NULL;
    p->prev = NULL;

    return p;

  }


// functie helper citire fisier
static char* read_file_content(const char *filename, int *size) {
    FILE *f = fopen(filename, "r");
    if (!f) {
        *size = 0;
        return NULL;
    }

    //mergem pana la final
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *content = (char *)malloc(fsize + 1);
    if (content) {
        fread(content, 1, fsize, f);
        content[fsize] = '\0';
        *size = (int)fsize;
    }
    
    fclose(f);
    return content;
}

TextEditor *create_table(const char *filename, const char *text,
                         int global_cursor) {

    TextEditor *editor = (TextEditor *)calloc(1, sizeof(TextEditor));
    if (!editor)
    return NULL;

    // initializare add buffer
    editor->add_buffer_capacity = 1024;
    editor->add_buffer = (char *)malloc(editor->add_buffer_capacity);
    if (!editor->add_buffer) {
        free(editor);
        return NULL;
    }

    char *text_initial = NULL;
    int length = 0;

    // luam textul din fisier sau din text
    if (filename) {
        text_initial = read_file_content(filename, &length);
    } else if (text) {
        length = strlen(text);
        text_initial = strdup(text);
    }

    if (text_initial && length > 0) {
        editor->original_buffer = text_initial;
        editor->original_size = length;
        editor->total_len = length;

        // facem prim ul piece
        Piece *first_piece = create_piece(ORIGINAL_BUFFER, 0, length);
        if (first_piece) {
            editor->head = first_piece;
            editor->tail = first_piece;
        }
    }

    //cursorul sa nu depaseasca limitele
    if (global_cursor < 0) global_cursor = 0;
    if (global_cursor > editor->total_len){
    global_cursor = editor->total_len;
    }
    editor->global_cursor = global_cursor;

    return editor;
}


void advance_cursor(TextEditor *editor, int advance) {

    if (!editor) 
    return;
    
    // asta e noua poz a cursorului
    int new_poz = editor->global_cursor + advance;
    
    // LIMITELE
    if (new_poz < 0) {
        new_poz = 0;
    }
    if (new_poz > editor->total_len) {
        new_poz = editor->total_len;
    }
    
    // setam la poz noua
    editor->global_cursor = new_poz;
}

int show_global_cursor(TextEditor *editor) {
  
  if(!editor)
  return 0;

  return editor->global_cursor;
}

int show_total_len(TextEditor *editor) {
  if(!editor)
  return 0;

  return editor->total_len;
}

void add_text(TextEditor *editor, char *text) {

  if (!editor || !text)
  return;
    
  int text_len = strlen(text);
  if (text_len == 0)
  return;

  // punem textul in add buffer
    if (editor->add_buffer_size + text_len >= editor->add_buffer_capacity) {
        editor->add_buffer_capacity *= 2;
        char *new_buffer = (char *)realloc(editor->add_buffer, editor->add_buffer_capacity);
        if (!new_buffer)
        return;
        editor->add_buffer = new_buffer;
    }

    int start_poz = editor->add_buffer_size;
    memcpy(editor->add_buffer + start_poz, text, text_len);
    editor->add_buffer_size += text_len;

// cream un piece nou
    Piece *new_piece = create_piece(ADD_BUFFER, start_poz, text_len);
    if (!new_piece)
    return;

// gasim poz de inserare
if (!editor->head) {
  // lista e goala
  editor->head = new_piece;
  editor->tail = new_piece;
  }
  else if (editor->global_cursor == 0) { // avem inserare la inceput
    new_piece->next = editor->head;
    editor->head->prev = new_piece;
    editor->head = new_piece;
  }
  else if (editor->global_cursor >= editor->total_len) { // inserare la final
    new_piece->prev = editor->tail;
    editor->tail->next = new_piece;
    editor->tail = new_piece;
  }
  else {
    // inserarea e la mijloc
    Piece *curr = editor->head;
    int current_pos = 0;

    while (curr != NULL) {
    if (current_pos + curr->len < editor->global_cursor) { // trebuie sa mergem mai departe ca sa ajungem unde vrem
        current_pos = current_pos + curr->len;
        curr = curr->next;
    } else {
        // am gasit piesa unde se afla cursoru sde opreste cautarea
        break;
    }
}

        // cursoru e intre piese
        if (current_pos == editor->global_cursor) {

    // inserare intre ele
    new_piece->next = curr;
    new_piece->prev = curr->prev;
    if (curr->prev) {
        curr->prev->next = new_piece;
    } else {
        editor->head = new_piece;  // daca curr e head
    }
    curr->prev = new_piece;
}
      else {
            // Split oiesa cyrenta
            int dist = editor->global_cursor - current_pos;
            
            // cream piesa din dreapta
            Piece *right_p = create_piece(curr->buffer, curr->start + dist, curr->len - dist);
            curr->len = dist; // scurtam piecul

            right_p->next = curr->next;
            right_p->prev = new_piece;
            if (curr->next) curr->next->prev = right_p;
            else editor->tail = right_p;

            new_piece->next = right_p;
            new_piece->prev = curr;
            curr->next = new_piece;
        }
    }

    editor->total_len += text_len;
    editor->global_cursor += text_len;
}
  


void delete_text(TextEditor *editor, int length) {
  
    if (!editor || length <= 0 || editor->global_cursor == 0)
    return;
    
    // nu stergem mai mult decat e
    if (length > editor->global_cursor) {
        length = editor->global_cursor;
    }
    
    // facem split la poz cursorului
    int current_pos = 0;
    Piece *curr = editor->head;
    
    // gasim piesa unde e cursoru
   while (curr != NULL) {
        // Vf daca cursoru e dupa piesa curenta
        if (current_pos + curr->len < editor->global_cursor) {
            current_pos += curr->len;
            curr = curr->next;
        } else {
            break;
        }
    }
    
    // cursoru e la mijl unei piese
    if (curr && current_pos < editor->global_cursor && current_pos + curr->len > editor->global_cursor) {
        
        int offset = editor->global_cursor - current_pos;
        Piece *right_p = create_piece(curr->buffer, curr->start + offset, curr->len - offset);
        if (!right_p) 
        return;
        
        curr->len = offset;
        
        right_p->next = curr->next;
        right_p->prev = curr;
        
        if (curr->next) {
            curr->next->prev = right_p;
        } else {
            editor->tail = right_p;
        }
        
        curr->next = right_p;
    }
    
    // piesa care se termina la  cursor
    Piece *p_actual = editor->head;
    int pos = 0;
    
    while (p_actual != NULL) {
        if (pos + p_actual->len < editor->global_cursor) {
            pos += p_actual->len;
            p_actual = p_actual->next;
        } else {
            break;
        }
    }
    
    //  stergem inapoi de la cursor
    int remaining_to_delete = length;
    
    while (remaining_to_delete > 0 && p_actual) {
        Piece *prev_piece = p_actual->prev;
        
        if (p_actual->len <= remaining_to_delete) {
            // cazul de a se sterge piesa intreaga
            remaining_to_delete -= p_actual->len;
            
            // eliminam din lista
            if (p_actual->prev) {
                p_actual->prev->next = p_actual->next;
            } else {
                editor->head = p_actual->next;
            }
            
            if (p_actual->next) {
                p_actual->next->prev = p_actual->prev;
            } else {
                editor->tail = p_actual->prev;
            }
            
            free(p_actual);
            p_actual = prev_piece;  // ne intoarcem la piesa anterioara
        } 
        else {
            // cazul in care scurtam piesa
            p_actual->len -= remaining_to_delete;
            remaining_to_delete = 0;
        }
    }
    
    //  actualizare
    editor->total_len -= length;
    editor->global_cursor -= length;
}


char *extract_current_text(TextEditor *editor) {

    if (!editor)
    return NULL;
    
    char *text_final = (char *)malloc(editor->total_len + 1);
    if (!text_final)
    return NULL;
    
    int offset = 0;
    Piece *curr = editor->head;
    
    while (curr) {
        char *source = NULL;
        
      if (curr->buffer == ORIGINAL_BUFFER) {
        source = editor->original_buffer;
        } else {
        source = editor->add_buffer;
        }
        
        if (source != NULL && curr->len > 0) {
            memcpy(text_final + offset, source + curr->start, curr->len);
            offset += curr->len;
        }
        
      curr = curr->next;
    }
    
    text_final[offset] = '\0';
    return text_final;
}

void save_current_text(TextEditor *editor, const char *filename, 
                       char **text, int *global_cursor) {
  
  if (!editor)
    return;

    // luam textul
    char *rezultat_text = extract_current_text(editor);
    if (rezultat_text == NULL)
    return;

    // returnam poz cursorului
    if (global_cursor != NULL) {
        *global_cursor = editor->global_cursor;
    }

    // salvam in fisier in filename
    if (filename != NULL) {
        FILE *fisier_iesire = fopen(filename, "w");
        if (fisier_iesire != NULL) {
            fwrite(rezultat_text, 1, editor->total_len, fisier_iesire);
            fclose(fisier_iesire);
        }
    }

    // returnarea textului prin pointer
    if (text != NULL) {
        *text = rezultat_text;
    } else {
        // trb sa i dam noi free
        free(rezultat_text);
    }
}

