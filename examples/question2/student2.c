#include <stdio.h>

void bubble_sort(int numbers[], int count)
{
    int pass, index, temporary;

    for (pass = 0; pass < count - 1; pass++)
    {
        /* Mistake: the inner loop stops one position too early. */
        for (index = 0; index < count - pass - 2; index++)
        {
            if (numbers[index] > numbers[index + 1])
            {
                temporary = numbers[index];
                numbers[index] = numbers[index + 1];
                numbers[index + 1] = temporary;
            }
        }
    }
}

int main(void)
{
    int numbers[100];
    int count, index;

    scanf("%d", &count);

    if (count < 1 || count > 100)
        return 1;

    for (index = 0; index < count; index++)
        scanf("%d", &numbers[index]);

    bubble_sort(numbers, count);

    for (index = 0; index < count; index++)
    {
        if (index > 0)
            printf(" ");
        printf("%d", numbers[index]);
    }

    printf("\n");
    return 0;
}