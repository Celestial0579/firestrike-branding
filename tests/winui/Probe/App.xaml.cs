using System.Globalization;
using System.Text.Json;
using System.Xml.Linq;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Markup;
using Microsoft.UI.Xaml.Media;
using Windows.UI;

namespace FsProbe;

// Aufruf: FsProbe.exe --thema Light|Dark|System --xaml <Firestrike.xaml> --aus <ergebnis.json>
// Schreibt für jeden Schlüssel der Datei den aufgelösten Wert, dazu einige Fluent-Schlüssel,
// an denen sich zeigt, ob die Akzentreihe greift. Jeder Fehler endet mit <aus>.fehler und Exit-Code 2.
public partial class App : Application
{
    private static readonly string[] Fluent =
    {
        "SystemAccentColor", "AccentFillColorDefaultBrush", "AccentTextFillColorPrimaryBrush",
        "TextOnAccentFillColorPrimaryBrush", "SystemColorWindowColor", "SystemColorWindowTextColor",
        "SystemColorHighlightColor", "SystemColorHotlightColor",
    };

    private Window? _fenster;

    public App()
    {
        var thema = Argument("--thema");
        if (thema == "Light") RequestedTheme = ApplicationTheme.Light;
        if (thema == "Dark") RequestedTheme = ApplicationTheme.Dark;
        UnhandledException += (_, e) => Abbrechen(e.Exception);
        InitializeComponent();
    }

    private static string Argument(string name)
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, name);
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : "";
    }

    private static void Abbrechen(Exception fehler)
    {
        File.WriteAllText(Argument("--aus") + ".fehler", fehler.ToString());
        Environment.Exit(2);
    }

    private static string Text(object? wert) => wert switch
    {
        Color c => $"#{c.A:X2}{c.R:X2}{c.G:X2}{c.B:X2}",
        SolidColorBrush b => $"#{b.Color.A:X2}{b.Color.R:X2}{b.Color.G:X2}{b.Color.B:X2}",
        double d => d.ToString(CultureInfo.InvariantCulture),
        CornerRadius r => r.TopLeft.ToString(CultureInfo.InvariantCulture),
        Thickness t => t.Left.ToString(CultureInfo.InvariantCulture),
        FontFamily f => f.Source,
        Windows.UI.Text.FontWeight w => w.Weight.ToString(CultureInfo.InvariantCulture),
        null => "<fehlt>",
        _ => wert.GetType().Name,
    };

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        try
        {
            XNamespace x = "http://schemas.microsoft.com/winfx/2006/xaml";
            var schluessel = XDocument.Load(Argument("--xaml")).Descendants()
                .Select(e => (string?)e.Attribute(x + "Key"))
                .Where(k => k is not null && k is not ("Light" or "Dark" or "HighContrast"))
                .Select(k => k!).Distinct().ToList();
            var ergebnis = new SortedDictionary<string, string>(StringComparer.Ordinal);
            foreach (var k in schluessel.Concat(Fluent))
            {
                Resources.TryGetValue(k, out var wert);
                ergebnis[k] = Text(wert);
            }

            // Jeder Pinsel einmal per ThemeResource in der Oberfläche: So lädt WinUI ihn wie eine App.
            var pinsel = schluessel.Where(k => k.EndsWith("Brush", StringComparison.Ordinal)).ToList();
            var xaml = "<StackPanel xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\">" +
                       string.Concat(pinsel.Select(k => $"<Border Height=\"2\" Background=\"{{ThemeResource {k}}}\" />")) +
                       "</StackPanel>";
            var stapel = (StackPanel)XamlReader.Load(xaml);
            _fenster = new Window { Content = stapel };
            stapel.Loaded += (_, _) =>
            {
                try
                {
                    for (var i = 0; i < pinsel.Count; i++)
                        ergebnis["ui:" + pinsel[i]] = Text(((Border)stapel.Children[i]).Background);
                    ergebnis["ui:ActualTheme"] = stapel.ActualTheme.ToString();
                    File.WriteAllText(Argument("--aus"), JsonSerializer.Serialize(ergebnis,
                        new JsonSerializerOptions { WriteIndented = true }));
                    Environment.Exit(0);
                }
                catch (Exception fehler)
                {
                    Abbrechen(fehler);
                }
            };
            _fenster.Activate();
        }
        catch (Exception fehler)
        {
            Abbrechen(fehler);
        }
    }
}
