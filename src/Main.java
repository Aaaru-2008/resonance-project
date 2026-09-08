import javax.swing.*;
import java.awt.*;
import java.util.Random;

public class Main extends JFrame {
    private final int gridSize = 5;
    private final JLabel maxTempLabel = new JLabel("--");
    private final JLabel avgTempLabel = new JLabel("--");
    private final JLabel hotspotLabel = new JLabel("--");
    private final JPanel gridPanel = new JPanel(new GridLayout(gridSize, gridSize, 6, 6));
    private final JTextArea actionArea = new JTextArea();

    public Main() {
        setTitle("Resonance Project - Heat UI");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(820, 620);
        setLocationRelativeTo(null);
        setLayout(new BorderLayout(15, 15));

        JPanel header = new JPanel();
        header.setBackground(new Color(15, 23, 42));
        header.setBorder(BorderFactory.createEmptyBorder(20, 20, 10, 20));

        JLabel title = new JLabel("Resonance Project");
        title.setForeground(Color.WHITE);
        title.setFont(new Font("Arial", Font.BOLD, 28));
        header.add(title);

        add(header, BorderLayout.NORTH);

        JPanel center = new JPanel(new BorderLayout(15, 15));
        center.setBorder(BorderFactory.createEmptyBorder(10, 20, 20, 20));

        JPanel statsPanel = new JPanel(new GridLayout(1, 3, 15, 10));
        statsPanel.setOpaque(false);

        statsPanel.add(makeStatCard("Max Temp", maxTempLabel, new Color(239, 68, 68)));
        statsPanel.add(makeStatCard("Avg Temp", avgTempLabel, new Color(59, 130, 246)));
        statsPanel.add(makeStatCard("Hotspots", hotspotLabel, new Color(249, 115, 22)));

        center.add(statsPanel, BorderLayout.NORTH);

        JPanel gridWrap = new JPanel(new BorderLayout());
        gridWrap.setBorder(BorderFactory.createTitledBorder("Temperature Grid"));
        gridWrap.add(gridPanel, BorderLayout.CENTER);
        center.add(gridWrap, BorderLayout.CENTER);

        JPanel side = new JPanel(new BorderLayout());
        side.setBorder(BorderFactory.createTitledBorder("Action Plan"));
        actionArea.setEditable(false);
        actionArea.setBackground(new Color(15, 23, 42));
        actionArea.setForeground(Color.WHITE);
        actionArea.setFont(new Font("Monospaced", Font.PLAIN, 14));
        actionArea.setLineWrap(true);
        actionArea.setWrapStyleWord(true);
        JScrollPane scroll = new JScrollPane(actionArea);
        side.add(scroll, BorderLayout.CENTER);

        JSplitPane splitPane = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, center, side);
        splitPane.setDividerLocation(520);
        splitPane.setResizeWeight(0.75);

        add(splitPane, BorderLayout.CENTER);

        JButton analyzeButton = new JButton("Analyze Heat");
        analyzeButton.setBackground(new Color(249, 115, 22));
        analyzeButton.setForeground(Color.WHITE);
        analyzeButton.setFocusPainted(false);
        analyzeButton.addActionListener(e -> runAnalysis());

        JPanel bottom = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        bottom.setBorder(BorderFactory.createEmptyBorder(0, 20, 20, 20));
        bottom.add(analyzeButton);
        add(bottom, BorderLayout.SOUTH);

        getContentPane().setBackground(new Color(15, 23, 42));
        runAnalysis();
    }

    private JPanel makeStatCard(String title, JLabel valueLabel, Color color) {
        JPanel card = new JPanel();
        card.setBackground(new Color(30, 41, 59));
        card.setBorder(BorderFactory.createLineBorder(color, 2));
        card.setLayout(new BorderLayout(5, 5));
        card.setPreferredSize(new Dimension(200, 100));

        JLabel titleLabel = new JLabel(title, SwingConstants.CENTER);
        titleLabel.setForeground(new Color(148, 163, 184));
        titleLabel.setFont(new Font("Arial", Font.BOLD, 14));

        valueLabel.setForeground(Color.WHITE);
        valueLabel.setHorizontalAlignment(SwingConstants.CENTER);
        valueLabel.setFont(new Font("Arial", Font.BOLD, 26));

        card.add(titleLabel, BorderLayout.NORTH);
        card.add(valueLabel, BorderLayout.CENTER);
        return card;
    }

    private void runAnalysis() {
        Random random = new Random();
        double[][] grid = new double[gridSize][gridSize];
        int hotspots = 0;
        double total = 0;

        gridPanel.removeAll();

        for (int row = 0; row < gridSize; row++) {
            for (int col = 0; col < gridSize; col++) {
                double temp = 28 + random.nextDouble() * 18;
                grid[row][col] = temp;
                total += temp;

                JLabel cell = new JLabel(String.format("%.1f", temp), SwingConstants.CENTER);
                cell.setOpaque(true);
                cell.setFont(new Font("Arial", Font.BOLD, 12));
                cell.setForeground(Color.BLACK);

                if (temp >= 38) {
                    hotspots++;
                    cell.setBackground(new Color(239, 68, 68));
                    cell.setToolTipText("Hotspot");
                } else if (temp >= 32) {
                    cell.setBackground(new Color(250, 204, 21));
                    cell.setToolTipText("Warm zone");
                } else {
                    cell.setBackground(new Color(34, 197, 94));
                    cell.setToolTipText("Cool zone");
                }

                gridPanel.add(cell);
            }
        }

        double avg = total / (gridSize * gridSize);
        double max = 0;
        for (int row = 0; row < gridSize; row++) {
            for (int col = 0; col < gridSize; col++) {
                max = Math.max(max, grid[row][col]);
            }
        }

        maxTempLabel.setText(String.format("%.1f°C", max));
        avgTempLabel.setText(String.format("%.1f°C", avg));
        hotspotLabel.setText(String.valueOf(hotspots));

        StringBuilder plan = new StringBuilder();
        plan.append("Heat Condition Summary\n");
        plan.append("- Maximum temperature: ").append(String.format("%.1f°C\n", max));
        plan.append("- Average temperature: ").append(String.format("%.1f°C\n", avg));
        plan.append("- Hotspots detected: ").append(hotspots).append("\n\n");
        plan.append("Recommended actions:\n");
        plan.append("1. Increase tree cover in hotspot zones\n");
        plan.append("2. Use reflective roofs and cool pavement\n");
        plan.append("3. Reduce impervious surfaces in dense areas\n");
        plan.append("4. Improve public awareness of heat risk\n");

        actionArea.setText(plan.toString());
        gridPanel.revalidate();
        gridPanel.repaint();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            Main app = new Main();
            app.setVisible(true);
        });
    }
}
