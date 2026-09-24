import SwiftUI
import UIKit

struct AppTextField: View {
    let title: String
    @Binding var text: String
    var isSecure = false
    var keyboard: UIKeyboardType = .default
    var axis: Axis = .horizontal

    var body: some View {
        Group {
            if isSecure {
                SecureField(title, text: $text)
            } else if axis == .vertical {
                if #available(iOS 16.0, *) {
                    TextField(title, text: $text, axis: .vertical)
                        .lineLimit(3...6)
                } else {
                    TextField(title, text: $text)
                        .lineLimit(3)
                }
            } else {
                TextField(title, text: $text)
            }
        }
        .textFieldStyle(.roundedBorder)
        .keyboardType(keyboard)
        .textInputAutocapitalization(.never)
        .autocorrectionDisabled()
    }
}

struct ErrorText: View {
    let message: String
    var body: some View {
        Text(message)
            .foregroundStyle(.red)
            .font(.callout)
    }
}

struct LoadingView: View {
    var body: some View {
        ProgressView()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct EmptyStateView: View {
    let message: String
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "tray")
                .font(.system(size: 48))
                .foregroundColor(.secondary)
            Text(message)
                .font(.headline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ChoicePicker: View {
    let label: String
    let options: [(value: String, label: String)]
    @Binding var selection: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label).font(.subheadline.weight(.semibold))
            Picker(label, selection: $selection) {
                ForEach(options, id: \.value) { option in
                    Text(option.label).tag(option.value)
                }
            }
            .pickerStyle(.menu)
        }
    }
}

/// Free-text field with catalog suggestions (web-style datalist).
/// The user can type any value; suggestions are optional shortcuts.
struct SuggestionTextField: View {
    let title: String
    @Binding var text: String
    let suggestions: [String]
    var placeholder: String = ""
    var maxSuggestions: Int = 8

    @FocusState private var focused: Bool
    @State private var showBrowser = false

    private var filtered: [String] {
        let query = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let matches: [String]
        if query.isEmpty {
            matches = Array(suggestions.prefix(maxSuggestions))
        } else {
            matches = suggestions
                .filter {
                    $0.localizedCaseInsensitiveContains(query)
                        && $0.caseInsensitiveCompare(query) != .orderedSame
                }
                .prefix(maxSuggestions)
                .map { $0 }
        }
        return matches
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.subheadline.weight(.semibold))
            HStack(spacing: 8) {
                TextField(placeholder.isEmpty ? title : placeholder, text: $text)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled()
                    .focused($focused)

                Button {
                    showBrowser = true
                } label: {
                    Image(systemName: "list.bullet")
                        .font(.body.weight(.medium))
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.bordered)
                .accessibilityLabel(title)
            }

            if focused, !filtered.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(filtered, id: \.self) { item in
                        Button {
                            text = item
                            focused = false
                        } label: {
                            Text(item)
                                .foregroundStyle(.primary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 10)
                                .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        if item != filtered.last {
                            Divider()
                        }
                    }
                }
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8))
            }
        }
        .sheet(isPresented: $showBrowser) {
            SuggestionBrowserSheet(
                title: title,
                suggestions: suggestions,
                selection: $text,
                isPresented: $showBrowser
            )
        }
    }
}

private struct SuggestionBrowserSheet: View {
    let title: String
    let suggestions: [String]
    @Binding var selection: String
    @Binding var isPresented: Bool
    @State private var query = ""

    private var filtered: [String] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        if q.isEmpty { return suggestions }
        return suggestions.filter { $0.localizedCaseInsensitiveContains(q) }
    }

    var body: some View {
        NavigationView {
            List {
                if !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    Button {
                        selection = query.trimmingCharacters(in: .whitespacesAndNewlines)
                        isPresented = false
                    } label: {
                        Label(query.trimmingCharacters(in: .whitespacesAndNewlines), systemImage: "plus.circle")
                    }
                }
                ForEach(filtered, id: \.self) { item in
                    Button(item) {
                        selection = item
                        isPresented = false
                    }
                    .foregroundStyle(.primary)
                }
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $query, prompt: title)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(tr("form.cancel")) { isPresented = false }
                }
            }
        }
    }
}

struct MetricCard: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.subheadline.weight(.semibold))
            Text(value).font(.title2.weight(.semibold))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
