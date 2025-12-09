// main.cpp - Notepad-- (Phase 6: Find/Replace & Polish)
#ifndef UNICODE
#define UNICODE
#endif 
#ifndef _UNICODE
#define _UNICODE
#endif

#include <windows.h>
#include <commdlg.h>
#include <string>
#include <cwctype>
#include <cstdio>
#include "resource.h"

// Global handles
HWND hEdit; 
HINSTANCE hInst;
WCHAR szTitle[] = L"Notepad--";
WCHAR szWindowClass[] = L"NotepadMinusMinus";
WCHAR szFileName[MAX_PATH] = L"Untitled";

// Globals for Find/Replace
HWND hFindReplaceDlg = NULL;    
UINT uFindReplaceMsg = 0;       
FINDREPLACE fr;                 
WCHAR szFindWhat[256];          
WCHAR szReplaceWith[256]; // New buffer for Replace

// Globals for Settings
HFONT hCurrentFont = NULL;
LOGFONT lfCurrentFont;
BOOL bWordWrap = FALSE;

// Encoding Enum
enum FileEncoding { ENC_ANSI, ENC_UTF16LE, ENC_UTF16BE, ENC_UTF8 };
FileEncoding currentEncoding = ENC_UTF8;

// Forward Declarations
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);
void ResizeEditControl(HWND hwndParent);
void SetDefaultFont();
void OpenFileHandler(HWND hwnd);
void SaveFileHandler(HWND hwnd, BOOL bSaveAs); 
BOOL SaveFileToDisk(HWND hwnd, LPCWSTR pszFileName);
BOOL LoadFileFromDisk(HWND hwnd, LPCWSTR pszFileName);
void FindNextText(HWND hwnd);
void ReplaceOne(HWND hwnd);
void ReplaceAll(HWND hwnd);
void InsertTimeDate(HWND hwnd);
void SelectFont(HWND hwnd);
void ToggleWordWrap(HWND hwnd);

// 1. Entry Point
int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow)
{
    hInst = hInstance;
    uFindReplaceMsg = RegisterWindowMessage(FINDMSGSTRING);

    WNDCLASSEXW wcex = {0};
    wcex.cbSize = sizeof(WNDCLASSEX);
    wcex.style          = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc    = WndProc;
    wcex.hInstance      = hInstance;
    wcex.hIcon          = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_ICON)); 
    wcex.hCursor        = LoadCursor(nullptr, IDC_ARROW);
    wcex.hbrBackground  = (HBRUSH)(COLOR_WINDOW+1);
    wcex.lpszMenuName   = MAKEINTRESOURCE(IDR_MAINMENU);
    wcex.lpszClassName  = szWindowClass;
    wcex.hIconSm        = LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_ICON));

    if (!RegisterClassExW(&wcex)) {
        MessageBox(NULL, L"Register Class Failed", L"Error", MB_OK);
        return 1;
    }

    HWND hWnd = CreateWindowW(szWindowClass, szTitle, WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT, 800, 600, nullptr, nullptr, hInstance, nullptr);

    if (!hWnd) {
        MessageBox(NULL, L"Create Window Failed", L"Error", MB_OK);
        return 1;
    }

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDR_ACCELERATOR));

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0))
    {
        if (hFindReplaceDlg != NULL && IsDialogMessage(hFindReplaceDlg, &msg)) continue;
        if (!TranslateAccelerator(hWnd, hAccelTable, &msg))
        {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }
    return (int) msg.wParam;
}

// 2. Window Procedure
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    // Handle Find/Replace Dialog Messages
    if (message == uFindReplaceMsg)
    {
        LPFINDREPLACE lpfr = (LPFINDREPLACE)lParam;
        
        // SYNC FLAGS: Ensure global struct matches the dialog's latest state
        fr.Flags = lpfr->Flags; 

        if (lpfr->Flags & FR_DIALOGTERM) { 
            hFindReplaceDlg = NULL; 
            return 0; 
        }

        if (lpfr->Flags & FR_FINDNEXT) { 
            FindNextText(hWnd); 
        }
        else if (lpfr->Flags & FR_REPLACE) {
            ReplaceOne(hWnd);
        }
        else if (lpfr->Flags & FR_REPLACEALL) {
            ReplaceAll(hWnd);
        }
        return 0;
    }

    switch (message)
    {
    case WM_CREATE:
        {
            hEdit = CreateWindowEx(WS_EX_CLIENTEDGE, L"EDIT", L"", 
                WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_HSCROLL | 
                ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL, 
                0, 0, 0, 0, hWnd, (HMENU)1, hInst, NULL);
            SetDefaultFont();
        }
        break;

    case WM_SIZE: ResizeEditControl(hWnd); break;
    case WM_SETFOCUS: SetFocus(hEdit); break;

    case WM_COMMAND:
        {
            int wmId = LOWORD(wParam);
            switch (wmId)
            {
            // FILE
            case ID_FILE_OPEN: OpenFileHandler(hWnd); break;
            case ID_FILE_SAVE: SaveFileHandler(hWnd, FALSE); break;
            case ID_FILE_SAVEAS: SaveFileHandler(hWnd, TRUE); break;
            case ID_FILE_NEW: 
                SetWindowText(hEdit, L""); 
                wcscpy(szFileName, L"Untitled");
                SetWindowText(hWnd, L"Notepad--");
                break;
            case ID_FILE_EXIT: DestroyWindow(hWnd); break;
            
            // PRINTING (Disabled per request)
            case ID_FILE_PRINT: MessageBox(hWnd, L"Printing not implemented.", L"Info", MB_OK); break;
            case ID_FILE_PAGESETUP: break; 

            // EDIT
            case ID_EDIT_UNDO: SendMessage(hEdit, EM_UNDO, 0, 0); break;
            case ID_EDIT_CUT: SendMessage(hEdit, WM_CUT, 0, 0); break;
            case ID_EDIT_COPY: SendMessage(hEdit, WM_COPY, 0, 0); break;
            case ID_EDIT_PASTE: SendMessage(hEdit, WM_PASTE, 0, 0); break;
            case ID_EDIT_DELETE: SendMessage(hEdit, WM_CLEAR, 0, 0); break;
            case ID_EDIT_SELECTALL: SendMessage(hEdit, EM_SETSEL, 0, -1); break;
            case ID_EDIT_TIMEDATE: InsertTimeDate(hWnd); break;
            
            case ID_EDIT_FIND:
                if (hFindReplaceDlg == NULL) {
                    ZeroMemory(&fr, sizeof(fr));
                    fr.lStructSize = sizeof(fr);
                    fr.hwndOwner = hWnd;
                    fr.lpstrFindWhat = szFindWhat;
                    fr.wFindWhatLen = 256;
                    fr.Flags = FR_DOWN | FR_NOWHOLEWORD; 
                    hFindReplaceDlg = FindText(&fr);
                }
                break;
            
            case ID_EDIT_REPLACE:
                if (hFindReplaceDlg == NULL) {
                    ZeroMemory(&fr, sizeof(fr));
                    fr.lStructSize = sizeof(fr);
                    fr.hwndOwner = hWnd;
                    fr.lpstrFindWhat = szFindWhat;
                    fr.wFindWhatLen = 256;
                    fr.lpstrReplaceWith = szReplaceWith;
                    fr.wReplaceWithLen = 256;
                    fr.Flags = FR_DOWN | FR_NOWHOLEWORD; 
                    hFindReplaceDlg = ReplaceText(&fr);
                }
                break;

            case ID_EDIT_FINDNEXT: 
                if (wcslen(szFindWhat) > 0) FindNextText(hWnd); 
                break;

            // FORMAT
            case ID_FORMAT_FONT: SelectFont(hWnd); break;
            case ID_FORMAT_WORDWRAP: ToggleWordWrap(hWnd); break;

            // HELP
            case ID_HELP_ABOUT: MessageBox(hWnd, L"Notepad-- v0.6\nClassic recreation.", L"About", MB_OK); break;
            
            default: return DefWindowProc(hWnd, message, wParam, lParam);
            }
        }
        break;

    case WM_DESTROY: PostQuitMessage(0); break;
    default: return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------------------------

void ResizeEditControl(HWND hwndParent)
{
    RECT rcClient;
    GetClientRect(hwndParent, &rcClient);
    SetWindowPos(hEdit, NULL, 0, 0, rcClient.right, rcClient.bottom, SWP_NOZORDER);
}

void SetDefaultFont()
{
    GetObject(GetStockObject(DEFAULT_GUI_FONT), sizeof(LOGFONT), &lfCurrentFont);
    wcscpy(lfCurrentFont.lfFaceName, L"Consolas");
    lfCurrentFont.lfHeight = -15; 
    lfCurrentFont.lfWeight = FW_NORMAL;
    hCurrentFont = CreateFontIndirect(&lfCurrentFont);
    SendMessage(hEdit, WM_SETFONT, (WPARAM)hCurrentFont, TRUE);
}

void InsertTimeDate(HWND hwnd)
{
    SYSTEMTIME st;
    GetLocalTime(&st);
    WCHAR szTime[100];
    swprintf_s(szTime, 100, L"%02d:%02d %s %02d/%02d/%d", 
        st.wHour > 12 ? st.wHour - 12 : (st.wHour == 0 ? 12 : st.wHour),
        st.wMinute, st.wHour >= 12 ? L"PM" : L"AM", st.wMonth, st.wDay, st.wYear);
    SendMessage(hEdit, EM_REPLACESEL, TRUE, (LPARAM)szTime);
}

void SelectFont(HWND hwnd)
{
    CHOOSEFONT cf = {0};
    cf.lStructSize = sizeof(cf);
    cf.hwndOwner = hwnd;
    cf.lpLogFont = &lfCurrentFont;
    cf.Flags = CF_SCREENFONTS | CF_EFFECTS | CF_INITTOLOGFONTSTRUCT;
    if (ChooseFont(&cf)) {
        HFONT hNewFont = CreateFontIndirect(&lfCurrentFont);
        if (hNewFont) {
            SendMessage(hEdit, WM_SETFONT, (WPARAM)hNewFont, TRUE);
            if (hCurrentFont) DeleteObject(hCurrentFont);
            hCurrentFont = hNewFont;
        }
    }
}

void ToggleWordWrap(HWND hwnd)
{
    bWordWrap = !bWordWrap;
    DWORD dwLen = GetWindowTextLength(hEdit);
    WCHAR* pText = new WCHAR[dwLen + 1];
    GetWindowText(hEdit, pText, dwLen + 1);
    DestroyWindow(hEdit);

    DWORD dwStyle = WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE | ES_AUTOVSCROLL;
    if (!bWordWrap) dwStyle |= (WS_HSCROLL | ES_AUTOHSCROLL); 

    hEdit = CreateWindowEx(WS_EX_CLIENTEDGE, L"EDIT", L"", dwStyle, 0, 0, 0, 0, hwnd, (HMENU)1, hInst, NULL);
    SendMessage(hEdit, WM_SETFONT, (WPARAM)hCurrentFont, TRUE);
    SetWindowText(hEdit, pText);
    delete[] pText;
    ResizeEditControl(hwnd);
    SetFocus(hEdit);
}

void FindNextText(HWND hwnd)
{
    DWORD dwLen = GetWindowTextLength(hEdit);
    WCHAR* pRawText = new WCHAR[dwLen + 1];
    GetWindowText(hEdit, pRawText, dwLen + 1);
    
    std::wstring text(pRawText);
    std::wstring search(szFindWhat);
    delete[] pRawText;

    DWORD dwStart, dwEnd;
    SendMessage(hEdit, EM_GETSEL, (WPARAM)&dwStart, (LPARAM)&dwEnd);

    bool bSearchDown = (fr.Flags & FR_DOWN) != 0;
    bool bMatchCase  = (fr.Flags & FR_MATCHCASE) != 0;

    if (!bMatchCase) {
        for (auto &c : text) c = towlower(c);
        for (auto &c : search) c = towlower(c);
    }

    size_t foundPos = std::string::npos;

    if (bSearchDown) {
        // Search Forward from END of selection
        foundPos = text.find(search, dwEnd);
    }
    else {
        // Search Backward from START of selection
        if (dwStart > 0) foundPos = text.rfind(search, dwStart - 1);
    }

    if (foundPos != std::string::npos) {
        int nStart = (int)foundPos;
        SendMessage(hEdit, EM_SETSEL, nStart, nStart + wcslen(szFindWhat));
        SendMessage(hEdit, EM_SCROLLCARET, 0, 0);
    }
    else {
        // CLASSIC BEHAVIOR: No Wrap Around, just error.
        MessageBox(hwnd, L"Cannot find text.", L"Notepad--", MB_ICONINFORMATION);
    }
}

void ReplaceOne(HWND hwnd)
{
    // Check if the CURRENT selection matches "Find What"
    DWORD dwStart, dwEnd;
    SendMessage(hEdit, EM_GETSEL, (WPARAM)&dwStart, (LPARAM)&dwEnd);
    
    DWORD dwLen = GetWindowTextLength(hEdit);
    WCHAR* pRawText = new WCHAR[dwLen + 1];
    GetWindowText(hEdit, pRawText, dwLen + 1);
    std::wstring text(pRawText);
    delete[] pRawText;

    std::wstring currentSelection = text.substr(dwStart, dwEnd - dwStart);
    std::wstring search(szFindWhat);
    
    bool bMatchCase  = (fr.Flags & FR_MATCHCASE) != 0;
    if (!bMatchCase) {
        for (auto &c : currentSelection) c = towlower(c);
        for (auto &c : search) c = towlower(c);
    }

    // If selection matches, replace it
    if (currentSelection == search) {
        SendMessage(hEdit, EM_REPLACESEL, TRUE, (LPARAM)szReplaceWith);
    }

    // Move to next
    FindNextText(hwnd);
}

void ReplaceAll(HWND hwnd)
{
    // Start from top
    SendMessage(hEdit, EM_SETSEL, 0, 0);
    
    int count = 0;
    
    // Naive Replace All Loop
    // We just call FindNextText. If it finds something, we check if it matches (it will) and replace it.
    // Note: We need a specialized loop here because FindNextText shows a MessageBox on failure, which we don't want during a loop.
    
    // Simplification: Let's do it on the std::wstring directly to be fast, then set text back.
    DWORD dwLen = GetWindowTextLength(hEdit);
    WCHAR* pRawText = new WCHAR[dwLen + 1];
    GetWindowText(hEdit, pRawText, dwLen + 1);
    std::wstring text(pRawText);
    delete[] pRawText;
    
    std::wstring search(szFindWhat);
    std::wstring replace(szReplaceWith);
    
    // This is case-sensitive replace logic for simplicity in std::wstring
    // Implementing case-insensitive replace all on the string buffer is complex. 
    // For now, we assume case sensitive or use the simple iterative approach:
    
    // ITERATIVE APPROACH (Visual)
    while (true) {
        // Find next position from current cursor? No, we have the string.
        // Let's do it purely in memory for speed/stability
        size_t pos = 0;
        bool bMatchCase = (fr.Flags & FR_MATCHCASE) != 0;
        
        std::wstring textLower = text;
        std::wstring searchLower = search;
        if (!bMatchCase) {
            for (auto &c : textLower) c = towlower(c);
            for (auto &c : searchLower) c = towlower(c);
        }

        // Find
        pos = bMatchCase ? text.find(search, pos) : textLower.find(searchLower, pos);
        
        if (pos == std::string::npos) break;
        
        // Replace in the real string
        text.replace(pos, search.length(), replace);
        
        // Update Lower string for next search (inefficient but safe)
        if (!bMatchCase) {
            textLower = text; 
            for (auto &c : textLower) c = towlower(c);
        }
        
        // Move pos forward
        pos += replace.length();
        count++;
    }

    if (count > 0) {
        SetWindowText(hEdit, text.c_str());
        WCHAR msg[100];
        swprintf_s(msg, 100, L"Replaced %d occurrences.", count);
        MessageBox(hwnd, msg, L"Notepad--", MB_OK);
    } else {
        MessageBox(hwnd, L"Cannot find text.", L"Notepad--", MB_ICONINFORMATION);
    }
}

// -----------------------------------------------------------------------------
// FILE I/O HANDLERS (Same as before)
// -----------------------------------------------------------------------------

void OpenFileHandler(HWND hwnd)
{
    OPENFILENAME ofn;
    WCHAR szFile[MAX_PATH] = L"";
    ZeroMemory(&ofn, sizeof(ofn));
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = hwnd;
    ofn.lpstrFile = szFile;
    ofn.nMaxFile = sizeof(szFile);
    ofn.lpstrFilter = L"Text Documents (*.txt)\0*.txt\0All Files (*.*)\0*.*\0";
    ofn.nFilterIndex = 1;
    ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST;

    if (GetOpenFileName(&ofn) == TRUE) {
        if (LoadFileFromDisk(hwnd, ofn.lpstrFile)) {
            wcscpy(szFileName, ofn.lpstrFile);
            std::wstring title = std::wstring(szFileName) + L" - Notepad--";
            SetWindowText(hwnd, title.c_str());
        }
    }
}

void SaveFileHandler(HWND hwnd, BOOL bSaveAs)
{
    if (bSaveAs || wcscmp(szFileName, L"Untitled") == 0) {
        OPENFILENAME ofn;
        WCHAR szFile[MAX_PATH] = L"";
        if (wcscmp(szFileName, L"Untitled") != 0) wcscpy(szFile, szFileName);
        ZeroMemory(&ofn, sizeof(ofn));
        ofn.lStructSize = sizeof(ofn);
        ofn.hwndOwner = hwnd;
        ofn.lpstrFile = szFile;
        ofn.nMaxFile = sizeof(szFile);
        ofn.lpstrFilter = L"Text Documents (*.txt)\0*.txt\0All Files (*.*)\0*.*\0";
        ofn.nFilterIndex = 1;
        ofn.lpstrDefExt = L"txt"; 
        ofn.Flags = OFN_PATHMUSTEXIST | OFN_OVERWRITEPROMPT;
        if (GetSaveFileName(&ofn) == TRUE) wcscpy(szFileName, ofn.lpstrFile);
        else return; 
    }
    if (SaveFileToDisk(hwnd, szFileName)) {
        std::wstring title = std::wstring(szFileName) + L" - Notepad--";
        SetWindowText(hwnd, title.c_str());
    }
}

BOOL LoadFileFromDisk(HWND hwnd, LPCWSTR pszFileName)
{
    HANDLE hFile = CreateFile(pszFileName, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return FALSE;
    DWORD dwFileSize = GetFileSize(hFile, NULL);
    if (dwFileSize == 0xFFFFFFFF) { CloseHandle(hFile); return FALSE; }
    unsigned char* pBuffer = new unsigned char[dwFileSize + 2];
    DWORD dwRead;
    if (!ReadFile(hFile, pBuffer, dwFileSize, &dwRead, NULL)) { delete[] pBuffer; CloseHandle(hFile); return FALSE; }
    pBuffer[dwFileSize] = 0; pBuffer[dwFileSize+1] = 0;
    CloseHandle(hFile);
    int headerOffset = 0;
    if (dwFileSize >= 3 && pBuffer[0] == 0xEF && pBuffer[1] == 0xBB && pBuffer[2] == 0xBF) { currentEncoding = ENC_UTF8; headerOffset = 3; }
    else if (dwFileSize >= 2 && pBuffer[0] == 0xFF && pBuffer[1] == 0xFE) { currentEncoding = ENC_UTF16LE; headerOffset = 2; }
    else if (dwFileSize >= 2 && pBuffer[0] == 0xFE && pBuffer[1] == 0xFF) { currentEncoding = ENC_UTF16BE; headerOffset = 2; }
    else {
        int nUtf8Len = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, (LPCSTR)pBuffer, dwFileSize, NULL, 0);
        if (nUtf8Len > 0 || dwFileSize == 0) { currentEncoding = ENC_UTF8; headerOffset = 0; }
        else { currentEncoding = ENC_ANSI; headerOffset = 0; }
    }
    WCHAR* pWideText = nullptr;
    int nWideLen = 0;
    if (currentEncoding == ENC_UTF16LE) {
        nWideLen = (dwFileSize - headerOffset) / 2; pWideText = new WCHAR[nWideLen + 1];
        memcpy(pWideText, pBuffer + headerOffset, nWideLen * sizeof(WCHAR)); pWideText[nWideLen] = 0; 
    }
    else if (currentEncoding == ENC_UTF16BE) {
        nWideLen = (dwFileSize - headerOffset) / 2; pWideText = new WCHAR[nWideLen + 1];
        unsigned char* pSrc = pBuffer + headerOffset; unsigned char* pDst = (unsigned char*)pWideText;
        for (int i = 0; i < nWideLen; i++) { pDst[2*i] = pSrc[2*i+1]; pDst[2*i+1] = pSrc[2*i]; }
        pWideText[nWideLen] = 0;
    }
    else if (currentEncoding == ENC_UTF8) {
        int nTextLen = dwFileSize - headerOffset;
        if (nTextLen > 0) {
            nWideLen = MultiByteToWideChar(CP_UTF8, 0, (LPCSTR)(pBuffer + headerOffset), nTextLen, NULL, 0);
            pWideText = new WCHAR[nWideLen + 1];
            MultiByteToWideChar(CP_UTF8, 0, (LPCSTR)(pBuffer + headerOffset), nTextLen, pWideText, nWideLen);
            pWideText[nWideLen] = 0;
        } else { pWideText = new WCHAR[1]; pWideText[0] = 0; }
    }
    else { 
        nWideLen = MultiByteToWideChar(CP_ACP, 0, (LPCSTR)pBuffer, dwFileSize, NULL, 0);
        pWideText = new WCHAR[nWideLen + 1];
        MultiByteToWideChar(CP_ACP, 0, (LPCSTR)pBuffer, dwFileSize, pWideText, nWideLen);
        pWideText[nWideLen] = 0;
    }
    SetWindowText(hEdit, pWideText);
    if (pWideText) delete[] pWideText;
    delete[] pBuffer;
    return TRUE;
}

BOOL SaveFileToDisk(HWND hwnd, LPCWSTR pszFileName)
{
    HANDLE hFile = CreateFile(pszFileName, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return FALSE;
    DWORD dwTextLength = GetWindowTextLength(hEdit);
    WCHAR* pszWideText = new WCHAR[dwTextLength + 1];
    GetWindowText(hEdit, pszWideText, dwTextLength + 1);
    DWORD dwWritten;
    BOOL bSuccess = TRUE;
    if (currentEncoding == ENC_UTF16LE) { unsigned char bom[] = { 0xFF, 0xFE }; WriteFile(hFile, bom, 2, &dwWritten, NULL); }
    else if (currentEncoding == ENC_UTF16BE) { unsigned char bom[] = { 0xFE, 0xFF }; WriteFile(hFile, bom, 2, &dwWritten, NULL); }
    else if (currentEncoding == ENC_UTF8) { unsigned char bom[] = { 0xEF, 0xBB, 0xBF }; WriteFile(hFile, bom, 3, &dwWritten, NULL); }

    if (currentEncoding == ENC_UTF16LE) { WriteFile(hFile, pszWideText, dwTextLength * sizeof(WCHAR), &dwWritten, NULL); }
    else if (currentEncoding == ENC_UTF16BE) {
        unsigned char* pSwapBuffer = new unsigned char[dwTextLength * 2];
        unsigned char* pSrc = (unsigned char*)pszWideText;
        for (DWORD i = 0; i < dwTextLength; i++) { pSwapBuffer[2*i] = pSrc[2*i+1]; pSwapBuffer[2*i+1] = pSrc[2*i]; }
        WriteFile(hFile, pSwapBuffer, dwTextLength * 2, &dwWritten, NULL); delete[] pSwapBuffer;
    }
    else if (currentEncoding == ENC_UTF8) {
        int nLen = WideCharToMultiByte(CP_UTF8, 0, pszWideText, -1, NULL, 0, NULL, NULL);
        char* pUtf8 = new char[nLen];
        WideCharToMultiByte(CP_UTF8, 0, pszWideText, -1, pUtf8, nLen, NULL, NULL);
        if (nLen > 1) WriteFile(hFile, pUtf8, nLen - 1, &dwWritten, NULL); delete[] pUtf8;
    }
    else { 
        int nLen = WideCharToMultiByte(CP_ACP, 0, pszWideText, -1, NULL, 0, NULL, NULL);
        char* pAnsi = new char[nLen];
        WideCharToMultiByte(CP_ACP, 0, pszWideText, -1, pAnsi, nLen, NULL, NULL);
        if (nLen > 1) WriteFile(hFile, pAnsi, nLen - 1, &dwWritten, NULL); delete[] pAnsi;
    }
    delete[] pszWideText;
    CloseHandle(hFile);
    return bSuccess;
}