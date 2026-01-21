import java.awt.*;
import javax.swing.*;

public class MyClass extends JFrame 
{
    public MyClass() {
        // x, y , width, height
        this.setBounds(50, 50, 500, 500);
        MyPanel panel = new MyPanel();
        this.add(panel);
        this.setVisible(true);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

    }
    
    class MyPanel extends JPanel {
        @Override
        protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        
        g.setColor(Color.RED);
        g.fillRect(50, 50, 100, 100);
        
        
    }
    }
    
    public static void main(String args[]) {
        new MyClass();
        
        // Random ints for RGB 
        int red = (int)(Math.random()*256);
        int green = (int)(Math.random()*256);
        int blue = (int)(Math.random()*256);
        

    }

}