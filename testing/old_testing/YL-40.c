#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <ncurses.h>

int main( int argc, char **argv )
{
        int i;
        int r;
        int fd;
        unsigned char command[2];
        unsigned char value[4];
        useconds_t delay = 2000;

        char *dev = "/dev/i2c-1";
        int addr = 0x48;

        int j;
        int key;

        initscr();
        noecho();
        cbreak();
        nodelay(stdscr, true);
        curs_set(0);
        printw("PCF8591 Output");

        mvaddstr(10, 0, "Brightness");
        mvaddstr(12, 0, "Temperature");
        mvaddstr(14, 0, "Water Sensor ");
        mvaddstr(16, 0, "Resistor");
        refresh();
        fd = open(dev, O_RDWR );
        if(fd < 0)
        {
                perror("Opening i2c device node\n");
                return 1;
        }

        r = ioctl(fd, I2C_SLAVE, addr);
        if(r < 0)
        {
                perror("Selecting i2c device\n");
        }

        command[1] = 0;
        while(1)
        {
                for(i = 0; i < 4; i++)
                {
                        command[0] = 0x40 | ((i + 1) & 0x03); // output enable | read input i
                        r = write(fd, &command, 2);
                        usleep(delay);
                        // the read is always one step behind the selected input
                        r = read(fd, &value[i], 1);
                        if(r != 1)
                        {
                                perror("reading i2c device\n");
                        }
                        usleep(delay);

                        value[i] = value[i] / 4;
                        move(10 + i + i, 12);

                        for(j = 0; j < 64; j++)
                        {
                                if(j < value[i])
                                {
                                        addch('*');
                                }
                                else
                                {
                                        addch(' ');
                                }
                        }
                }
                refresh();

                key = getch();
                if(key == 43)
                {
                        command[1]++;
                }
                else if(key == 45)
                {
                        command[1]--;
                }
                else if(key > -1)
                {
                        break;
                }
        }

        endwin();
        close(fd);
        printf("%d\n", key);
        return(0);
}