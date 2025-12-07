// main.cpp - Notepad-- (Phase 4)
#ifndef UNICODE
#define UNICODE
#endif 
#ifndef _UNICODE
#define _UNICODE
#endif

#include <windows.h>
#include <commdlg.h>
#include <string>
#include "resource.h"

// Global handles
HWND hEdit; 
HINSTANCE hInst;
WCHAR szTitle[] = L"Notepad--";
WCHAR szWindowClass[] = L"NotepadMinusMinus";
WCHAR szFileName[MAX_PATH] = L"Untitled";
// NEW GLOBALS FOR FIND FEATURE
HWND hFindReplaceDlg = NULL;    // Handle to the floating Find dialog
UINT uFindReplaceMsg = 0;       // Message identifier for Find events
FINDREPLACE fr;                 // Structure for Find dialog parameters
WCHAR szFindWhat[80];           // Buffer for the search string

// NEW: Encoding support
enum FileEncoding {
    ENC_ANSI,
    ENC_UTF16LE, // Windows "Unicode"
    ENC_UTF16BE,
    ENC_UTF8
};

FileEncoding currentEncoding = ENC_UTF8; // Default to modern UTF-8 for new files

// Forward declarations
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);
void ResizeEditControl(HWND hwndParent);
void SetDefaultFont();
void OpenFileHandler(HWND hwnd);
void SaveFileHandler(HWND hwnd, BOOL bSaveAs); // Updated prototype
BOOL SaveFileToDisk(HWND hwnd, LPCWSTR pszFileName);
BOOL LoadFileFromDisk(HWND hwnd, LPCWSTR pszFileName);
void FindNextText(HWND hwnd);

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
        MessageBox(NULL, L"Call to RegisterClassExW failed!", L"Error", MB_OK);
        return 1;
    }

    HWND hWnd = CreateWindowW(
        szWindowClass, szTitle, WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT, 800, 600, 
        nullptr, nullptr, hInstance, nullptr
    );

    if (!hWnd) {
        MessageBox(NULL, L"Call to CreateWindowW failed!", L"Error", MB_OK);
        return 1;
    }

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    // --- NEW: Load Accelerators ---
    HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDR_ACCELERATOR));

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0))
    {
        // Priority 1: Find Dialog Messages
        if (hFindReplaceDlg != NULL && IsDialogMessage(hFindReplaceDlg, &msg))
        {
            continue;
        }

        // Priority 2: Keyboard Shortcuts (Accelerators)
        if (!TranslateAccelerator(hWnd, hAccelTable, &msg))
        {
            // Priority 3: Standard Windows Messages
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

    return (int) msg.wParam;
}

// 2. Window Procedure
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    // --- NEW: Handle the Find Dialog Message ---
    if (message == uFindReplaceMsg)
    {
        LPFINDREPLACE lpfr = (LPFINDREPLACE)lParam;
        
        // If the dialog is closing
        if (lpfr->Flags & FR_DIALOGTERM)
        {
            hFindReplaceDlg = NULL;
            return 0;
        }

        // If the user clicked "Find Next"
        if (lpfr->Flags & FR_FINDNEXT)
        {
            FindNextText(hWnd);
        }
        return 0;
    }
    // -------------------------------------------

    switch (message)
    {
    case WM_CREATE:
        // ... (Keep existing code)
        hEdit = CreateWindowEx(
            WS_EX_CLIENTEDGE, L"EDIT", L"", 
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_HSCROLL | 
            ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL, 
            0, 0, 0, 0, hWnd, (HMENU)1, hInst, NULL
        );
        SetDefaultFont();
        break;

    // ... (Keep WM_SIZE, WM_SETFOCUS)
    case WM_SIZE: ResizeEditControl(hWnd); break;
    case WM_SETFOCUS: SetFocus(hEdit); break;

    case WM_COMMAND:
        {
            int wmId = LOWORD(wParam);
            switch (wmId)
            {
            // ... (Keep File I/O cases)
            case ID_FILE_OPEN: OpenFileHandler(hWnd); break;
            case ID_FILE_SAVE: SaveFileHandler(hWnd, FALSE); break;
            case ID_FILE_SAVEAS: SaveFileHandler(hWnd, TRUE); break;
            case ID_FILE_EXIT: DestroyWindow(hWnd); break;
            
            // --- NEW: Find Command ---
            case ID_EDIT_FIND:
                if (hFindReplaceDlg == NULL)
                {
                    ZeroMemory(&fr, sizeof(fr));
                    fr.lStructSize = sizeof(fr);
                    fr.hwndOwner = hWnd;
                    fr.lpstrFindWhat = szFindWhat;
                    fr.wFindWhatLen = 80;
                    fr.Flags = FR_DOWN | FR_NOWHOLEWORD; 

                    hFindReplaceDlg = FindText(&fr);
                }
                break;
            // -------------------------

            case ID_HELP_ABOUT:
                MessageBox(hWnd, L"Notepad-- v0.3\nClassic recreation.", L"About", MB_OK);
                break;
            case ID_EDIT_SELECTALL:
                SendMessage(hEdit, EM_SETSEL, 0, -1);
                break;
            default:
                return DefWindowProc(hWnd, message, wParam, lParam);
            }
        }
        break;

    case WM_DESTROY:
        PostQuitMessage(0);
        break;

    default:
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}

// Helpers
void ResizeEditControl(HWND hwndParent)
{
    RECT rcClient;
    GetClientRect(hwndParent, &rcClient);
    SetWindowPos(hEdit, NULL, 0, 0, rcClient.right, rcClient.bottom, SWP_NOZORDER);
}

void SetDefaultFont()
{
    HFONT hFont = CreateFont(20, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, ANSI_CHARSET, 
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY, 
        DEFAULT_PITCH | FF_MODERN, L"Consolas");
    SendMessage(hEdit, WM_SETFONT, (WPARAM)hFont, TRUE);
}

// -----------------------------------------------------------------------------
// File I/O Handlers
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

    if (GetOpenFileName(&ofn) == TRUE)
    {
        if (LoadFileFromDisk(hwnd, ofn.lpstrFile))
        {
            wcscpy(szFileName, ofn.lpstrFile);
            std::wstring title = std::wstring(szFileName) + L" - Notepad--";
            SetWindowText(hwnd, title.c_str());
        }
    }
}

void SaveFileHandler(HWND hwnd, BOOL bSaveAs)
{
    // If it's "Save As" OR the file is currently "Untitled", show the dialog
    if (bSaveAs || wcscmp(szFileName, L"Untitled") == 0)
    {
        OPENFILENAME ofn;
        WCHAR szFile[MAX_PATH] = L"";

        // Pre-fill the dialog with the current filename if it's not "Untitled"
        if (wcscmp(szFileName, L"Untitled") != 0) {
            wcscpy(szFile, szFileName);
        }

        ZeroMemory(&ofn, sizeof(ofn));
        ofn.lStructSize = sizeof(ofn);
        ofn.hwndOwner = hwnd;
        ofn.lpstrFile = szFile;
        ofn.nMaxFile = sizeof(szFile);
        ofn.lpstrFilter = L"Text Documents (*.txt)\0*.txt\0All Files (*.*)\0*.*\0";
        ofn.nFilterIndex = 1;
        ofn.lpstrDefExt = L"txt"; // <--- This forces the .txt extension
        ofn.Flags = OFN_PATHMUSTEXIST | OFN_OVERWRITEPROMPT;

        if (GetSaveFileName(&ofn) == TRUE)
        {
            wcscpy(szFileName, ofn.lpstrFile);
        }
        else
        {
            return; // User cancelled
        }
    }

    if (SaveFileToDisk(hwnd, szFileName))
    {
        std::wstring title = std::wstring(szFileName) + L" - Notepad--";
        SetWindowText(hwnd, title.c_str());
    }
}

void FindNextText(HWND hwnd)
{
    // 1. Get the current text and selection
    DWORD dwLen = GetWindowTextLength(hEdit);
    WCHAR* pRawText = new WCHAR[dwLen + 1];
    GetWindowText(hEdit, pRawText, dwLen + 1);
    
    std::wstring text(pRawText);
    std::wstring search(szFindWhat);
    delete[] pRawText;

    DWORD dwStart, dwEnd;
    SendMessage(hEdit, EM_GETSEL, (WPARAM)&dwStart, (LPARAM)&dwEnd);

    // 2. Check Direction
    // The Find Dialog sets the FR_DOWN flag if "Down" is checked.
    bool bSearchDown = (fr.Flags & FR_DOWN) != 0;
    bool bMatchCase  = (fr.Flags & FR_MATCHCASE) != 0;

    // 3. Handle Case Sensitivity (Primitive method: lowercase both if unchecked)
    if (!bMatchCase) {
        for (auto &c : text) c = towlower(c);
        for (auto &c : search) c = towlower(c);
    }

    size_t foundPos = std::string::npos;

    if (bSearchDown)
    {
        // Search Forward from the END of the current selection
        foundPos = text.find(search, dwEnd);
    }
    else
    {
        // Search Backward (Up) from the START of the current selection
        // We look for the LAST occurrence that happens before dwStart
        if (dwStart > 0)
            foundPos = text.rfind(search, dwStart - 1);
    }

    // 4. Handle Result
    if (foundPos != std::string::npos)
    {
        int nStart = (int)foundPos;
        
        // Fix: Removed the erroneous 'nEnd' line. 
        // We calculate the end position directly in the Select command below.
        SendMessage(hEdit, EM_SETSEL, nStart, nStart + wcslen(szFindWhat));
        SendMessage(hEdit, EM_SCROLLCARET, 0, 0);
    }
    else
    {
        MessageBox(hwnd, L"Cannot find text.", L"Notepad--", MB_ICONINFORMATION);
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
    if (!ReadFile(hFile, pBuffer, dwFileSize, &dwRead, NULL))
    {
        delete[] pBuffer;
        CloseHandle(hFile);
        return FALSE;
    }
    pBuffer[dwFileSize] = 0;
    pBuffer[dwFileSize+1] = 0;

    CloseHandle(hFile);

    // --- ENCODING DETECTION ---
    int headerOffset = 0;

    // 1. Check for Explicit BOMs
    if (dwFileSize >= 3 && pBuffer[0] == 0xEF && pBuffer[1] == 0xBB && pBuffer[2] == 0xBF) {
        currentEncoding = ENC_UTF8;
        headerOffset = 3;
    }
    else if (dwFileSize >= 2 && pBuffer[0] == 0xFF && pBuffer[1] == 0xFE) {
        currentEncoding = ENC_UTF16LE;
        headerOffset = 2;
    }
    else if (dwFileSize >= 2 && pBuffer[0] == 0xFE && pBuffer[1] == 0xFF) {
        currentEncoding = ENC_UTF16BE;
        headerOffset = 2;
    }
    else 
    {
        // 2. No BOM? Try to detect "UTF-8 without BOM"
        // We attempt to convert the buffer using CP_UTF8 with the MB_ERR_INVALID_CHARS flag.
        // If this succeeds, it is valid UTF-8. If it fails, it contains invalid bytes, so it's likely ANSI.
        int nUtf8Len = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, (LPCSTR)pBuffer, dwFileSize, NULL, 0);
        
        if (nUtf8Len > 0 || dwFileSize == 0) 
        {
            currentEncoding = ENC_UTF8;
            headerOffset = 0;
        }
        else 
        {
            currentEncoding = ENC_ANSI;
            headerOffset = 0;
        }
    }

    // --- CONVERSION TO WINDOWS TEXT (WCHAR) ---
    WCHAR* pWideText = nullptr;
    int nWideLen = 0;

    if (currentEncoding == ENC_UTF16LE)
    {
        nWideLen = (dwFileSize - headerOffset) / 2;
        pWideText = new WCHAR[nWideLen + 1];
        memcpy(pWideText, pBuffer + headerOffset, nWideLen * sizeof(WCHAR));
        pWideText[nWideLen] = 0; 
    }
    else if (currentEncoding == ENC_UTF16BE)
    {
        nWideLen = (dwFileSize - headerOffset) / 2;
        pWideText = new WCHAR[nWideLen + 1];
        unsigned char* pSrc = pBuffer + headerOffset;
        unsigned char* pDst = (unsigned char*)pWideText;
        for (int i = 0; i < nWideLen; i++) {
            pDst[2*i]     = pSrc[2*i+1];
            pDst[2*i+1]   = pSrc[2*i];
        }
        pWideText[nWideLen] = 0;
    }
    else if (currentEncoding == ENC_UTF8)
    {
        int nTextLen = dwFileSize - headerOffset;
        if (nTextLen > 0) {
            // Note: We do NOT use MB_ERR_INVALID_CHARS here because we want to load as much as possible, 
            // even if there is a tiny error somewhere.
            nWideLen = MultiByteToWideChar(CP_UTF8, 0, (LPCSTR)(pBuffer + headerOffset), nTextLen, NULL, 0);
            pWideText = new WCHAR[nWideLen + 1];
            MultiByteToWideChar(CP_UTF8, 0, (LPCSTR)(pBuffer + headerOffset), nTextLen, pWideText, nWideLen);
            pWideText[nWideLen] = 0;
        } else {
            pWideText = new WCHAR[1]; pWideText[0] = 0;
        }
    }
    else // ANSI
    {
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

    // 1. Write BOM (if needed)
    if (currentEncoding == ENC_UTF16LE) {
        unsigned char bom[] = { 0xFF, 0xFE };
        WriteFile(hFile, bom, 2, &dwWritten, NULL);
    }
    else if (currentEncoding == ENC_UTF16BE) {
        unsigned char bom[] = { 0xFE, 0xFF };
        WriteFile(hFile, bom, 2, &dwWritten, NULL);
    }
    else if (currentEncoding == ENC_UTF8) {
        unsigned char bom[] = { 0xEF, 0xBB, 0xBF };
        WriteFile(hFile, bom, 3, &dwWritten, NULL);
    }

    // 2. Convert and Write Content
    if (currentEncoding == ENC_UTF16LE) {
        // Native Windows format, just write the WCHAR buffer directly
        WriteFile(hFile, pszWideText, dwTextLength * sizeof(WCHAR), &dwWritten, NULL);
    }
    else if (currentEncoding == ENC_UTF16BE) {
        // Swap bytes before writing
        unsigned char* pSwapBuffer = new unsigned char[dwTextLength * 2];
        unsigned char* pSrc = (unsigned char*)pszWideText;
        for (DWORD i = 0; i < dwTextLength; i++) {
            pSwapBuffer[2*i]     = pSrc[2*i+1];
            pSwapBuffer[2*i+1]   = pSrc[2*i];
        }
        WriteFile(hFile, pSwapBuffer, dwTextLength * 2, &dwWritten, NULL);
        delete[] pSwapBuffer;
    }
    else if (currentEncoding == ENC_UTF8) {
        int nLen = WideCharToMultiByte(CP_UTF8, 0, pszWideText, -1, NULL, 0, NULL, NULL);
        char* pUtf8 = new char[nLen];
        WideCharToMultiByte(CP_UTF8, 0, pszWideText, -1, pUtf8, nLen, NULL, NULL);
        // nLen includes null terminator, don't write that
        if (nLen > 1) WriteFile(hFile, pUtf8, nLen - 1, &dwWritten, NULL);
        delete[] pUtf8;
    }
    else { // ANSI
        int nLen = WideCharToMultiByte(CP_ACP, 0, pszWideText, -1, NULL, 0, NULL, NULL);
        char* pAnsi = new char[nLen];
        WideCharToMultiByte(CP_ACP, 0, pszWideText, -1, pAnsi, nLen, NULL, NULL);
        if (nLen > 1) WriteFile(hFile, pAnsi, nLen - 1, &dwWritten, NULL);
        delete[] pAnsi;
    }

    delete[] pszWideText;
    CloseHandle(hFile);
    return bSuccess;
}