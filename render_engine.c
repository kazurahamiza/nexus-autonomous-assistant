#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void render_universal_stream(const char *segment_list, const char *output_file, 
                            int fps, const char *bitrate, 
                            const char *genre, const char *rating) {
    FILE *file = fopen(segment_list, "r");
    if (!file) {
        printf("[C ERROR] Manifest file missing.\n");
        return;
    }

    printf("[C ENGINE] Rendering pipeline initiated.\n");
    printf("[C ENGINE] FPS: %d | Bitrate: %s | Genre: %s | Rating: %s\n", fps, bitrate, genre, rating);

    /* Construct FFmpeg command with dynamic metadata injection:
     * -metadata genre="..."
     * -metadata rating="..."
     * -r fps setting
     */
    char command[1024];
    snprintf(command, sizeof(command),
             "ffmpeg -y -r %d -f concat -safe 0 -i %s -c:v hevc_nvenc -b:v %s "
             "-metadata genre=\"%s\" -metadata comment=\"Rating: %s\" "
             "-pix_fmt yuv420p -c:a aac -b:a 128k %s",
             fps, segment_list, bitrate, genre, rating, output_file);

    int result = system(command);

    if (result == 0) {
        printf("[C ENGINE] Render completed with metadata tags applied.\n");

        // Immediate cleanup of temporary segment files
        rewind(file);
        char line[256];
        while (fgets(line, sizeof(line), file)) {
            line[strcspn(line, "\r\n")] = 0;
            if (strncmp(line, "file ", 5) == 0) {
                char *filename = line + 5;
                remove(filename);
            }
        }
    }
    fclose(file);
}

int main(int argc, char *argv[]) {
    if (argc < 7) {
        printf("Usage: %s <segments.txt> <output.mp4> <fps> <bitrate> <genre> <rating>\n", argv[0]);
        return 1;
    }

    render_universal_stream(argv[1], argv[2], atoi(argv[3]), argv[4], argv[5], argv[6]);
    return 0;
}
